from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Depends
from fastapi.responses import FileResponse
import os
from dotenv import load_dotenv
import uuid
import logging
import requests
import base64
import json
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.services.pdf_service import create_pdf_record, process_pdf, get_pdf_document, get_pdf_pages
from openai import OpenAI

# 加载环境变量
load_dotenv()

router = APIRouter()
logger = logging.getLogger(__name__)

# 配置
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", "104857600"))  # 默认100MB

@router.post("/upload")
async def upload_pdf(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    上传PDF文件
    """
    # 检查文件类型
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="只支持PDF文件")
    
    # 检查文件大小
    contents = await file.read()
    logger.info(f"文件大小: {len(contents)} 字节")
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code = 413, detail=f"文件大小超过限制 ({MAX_FILE_SIZE / 1048576}MB)")
    
    # 生成唯一文件名
    file_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{file_id}.pdf")
    
    # 保存文件
    try:
        with open(file_path, "wb") as f:
            f.write(contents)
        
        logger.info(f"文件上传成功: {file.filename} -> {file_id}.pdf")
        
        # 创建数据库记录
        db = next(get_db())
        try:
            create_pdf_record(db, file_id, file.filename, file_path)
            
            # 添加后台任务处理PDF
            background_tasks.add_task(process_pdf_background, file_id, file_path)
        finally:
            db.close()
        
        return {
            "file_id": file_id,
            "original_filename": file.filename,
            "status": "uploaded",
            "message": "文件上传成功，等待处理"
        }
    except Exception as e:
        logger.error(f"文件保存失败: {str(e)}")
        raise HTTPException(status_code=500, detail="文件保存失败")

@router.get("/status/{file_id}")
async def get_file_status(file_id: str, db: Session = Depends(get_db)):
    """
    获取文件处理状态
    """
    pdf_doc = get_pdf_document(db, file_id)
    if not pdf_doc:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    # 获取页面信息
    pages = get_pdf_pages(db, file_id)
    
    return {
        "file_id": file_id,
        "original_filename": pdf_doc.original_filename,
        "status": pdf_doc.status.value,
        "total_pages": pdf_doc.total_pages,
        "pages_processed": len([p for p in pages if p.ocr_status]),
        "error_message": pdf_doc.error_message,
        "created_at": pdf_doc.created_at
    }

@router.get("/ocr/{file_id}")
async def get_ocr_results(file_id: str, page: int = None, db: Session = Depends(get_db)):
    """
    获取OCR识别结果
    
    - **file_id**: PDF文件ID
    - **page**: 页码（可选，不提供则返回所有页的结果）
    """
    pdf_doc = get_pdf_document(db, file_id)
    if not pdf_doc:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    # 获取页面信息
    pages = get_pdf_pages(db, file_id)
    
    # 如果指定了页码，返回单页结果
    if page is not None:
        target_page = next((p for p in pages if p.page_number == page), None)
        if not target_page:
            raise HTTPException(status_code=404, detail=f"页码 {page} 不存在")
        if not target_page.ocr_status:
            raise HTTPException(status_code=400, detail=f"页码 {page} 的OCR识别尚未完成")
        
        return {
            "file_id": file_id,
            "page": page,
            "text": target_page.ocr_text,
            "processed_at": target_page.processed_at
        }
    
    # 返回所有页的结果
    results = []
    for p in pages:
        if p.ocr_status:
            results.append({
                "page": p.page_number,
                "text": p.ocr_text,
                "processed_at": p.processed_at
            })
    
    return {
        "file_id": file_id,
        "original_filename": pdf_doc.original_filename,
        "total_pages": pdf_doc.total_pages,
        "pages_with_ocr": len(results),
        "results": results
    }

@router.get("/files")
async def get_pdf_files_list(db: Session = Depends(get_db)):
    """
    获取所有PDF文件列表
    
    返回系统中所有上传的PDF文件信息，包括文件ID、原始文件名、处理状态等
    """
    from app.database.models import PDFDocument
    
    try:
        # 从数据库获取所有PDF记录，按创建时间倒序排列
        pdf_documents = db.query(PDFDocument).order_by(PDFDocument.created_at.desc()).all()
        
        # 构建响应数据
        files_list = []
        for doc in pdf_documents:
            # 获取页面信息，计算已处理的页面数
            pages = get_pdf_pages(db, doc.id)
            pages_processed = len([p for p in pages if p.ocr_status])
            
            files_list.append({
                "id": doc.id,
                "original_filename": doc.original_filename,
                "status": doc.status.value,
                "total_pages": doc.total_pages,
                "pages_processed": pages_processed,
                "error_message": doc.error_message,
                "created_at": doc.created_at,
                "updated_at": doc.updated_at
            })
        
        return {
            "total": len(files_list),
            "files": files_list
        }
    except Exception as e:
        logger.error(f"获取PDF文件列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取文件列表失败")

@router.get("/{file_id}")
async def download_pdf(file_id: str, db: Session = Depends(get_db)):
    """
    下载PDF文件
    
    通过文件ID直接返回PDF文件
    
    - **file_id**: PDF文件ID
    """
    try:
        # 获取PDF文档信息
        pdf_doc = get_pdf_document(db, file_id)
        if not pdf_doc:
            raise HTTPException(status_code=404, detail="文件不存在")
        
        # 检查文件是否存在
        file_path = pdf_doc.file_path
        if not os.path.exists(file_path):
            logger.error(f"文件路径不存在: {file_path}")
            raise HTTPException(status_code=404, detail="文件不存在于服务器")
        
        # 返回文件
        return FileResponse(
            path=file_path,
            filename=pdf_doc.original_filename,
            media_type="application/pdf"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"下载PDF文件失败: {str(e)}")
        raise HTTPException(status_code=500, detail="下载文件失败")

from pydantic import BaseModel
class TextItem(BaseModel):
    content: str
    page_number: int

@router.post("/content/{file_id}")
async def save_text(file_id: str, item: TextItem, db: Session = Depends(get_db)):
    """
    - **file_id**: PDF文件ID
    - **content**: OCR识别内容
    """
    try:
        from app.database.models import PDFPage
        from datetime import datetime

        page = db.query(PDFPage).filter(
            PDFPage.document_id == file_id,
            PDFPage.page_number == item.page_number
        ).first()
        
        # 检查文件是否存在
        if not page:
            raise HTTPException(status_code=404, detail=f"页码 {item.page_number} 不存在")
        
        page.ocr_text = item.content
        page.ocr_status = True
        page.updated_at = datetime.now()

        db.commit()
        
        # 返回文件
        return {
            "file_id": file_id,
            "status": "success",
            "message": "保存成功"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"保存失败: {str(e)}")
        raise HTTPException(status_code=500, detail="保存失败")

@router.delete("/{file_id}")
async def delete_pdf(file_id: str, db: Session = Depends(get_db)):
    """
    删除PDF文件
    
    通过文件ID删除PDF文件及其相关数据
    
    - **file_id**: PDF文件ID
    """
    try:
        # 获取PDF文档信息
        pdf_doc = get_pdf_document(db, file_id)
        if not pdf_doc:
            raise HTTPException(status_code=404, detail="文件不存在")
        
        # 删除物理文件
        file_path = pdf_doc.file_path
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"成功删除PDF文件: {file_path}")
            except Exception as e:
                logger.error(f"删除PDF文件失败: {str(e)}")
        
        # 删除相关的图片文件夹
        image_dir = os.path.join("images", file_id)
        if os.path.exists(image_dir) and os.path.isdir(image_dir):
            try:
                import shutil
                shutil.rmtree(image_dir)
                logger.info(f"成功删除图片文件夹: {image_dir}")
            except Exception as e:
                logger.error(f"删除图片文件夹失败: {str(e)}")
        
        # 从数据库删除记录
        from app.database.models import PDFPage
        # 先删除相关的页面记录
        db.query(PDFPage).filter(PDFPage.document_id == file_id).delete()
        # 再删除文档记录
        db.delete(pdf_doc)
        db.commit()
        
        logger.info(f"成功删除PDF文档记录: {file_id}")
        return {"message": "文件删除成功", "file_id": file_id}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"删除PDF文件失败: {str(e)}")
        raise HTTPException(status_code=500, detail="删除文件失败")

@router.get("/{file_id}/info")
async def get_pdf_info(file_id: str, db: Session = Depends(get_db)):
    """
    获取PDF文件信息
    
    通过文件ID获取PDF文件路径和图片列表
    
    - **file_id**: PDF文件ID
    """
    try:
        # 获取PDF文档信息
        pdf_doc = get_pdf_document(db, file_id)
        if not pdf_doc:
            raise HTTPException(status_code=404, detail="文件不存在")
        
        # 获取文件路径
        file_path = pdf_doc.file_path
        file_exists = os.path.exists(file_path)
        
        # 查询页面记录
        from app.database.models import PDFPage
        pages = db.query(PDFPage).filter(PDFPage.document_id == file_id).all()
        
        # 构建页面数据列表
        pages_data = []
        for page in pages:
            pages_data.append({
                "id": page.id,
                "document_id": page.document_id,
                "page_number": page.page_number,
                "ocr_text": page.ocr_text,
                "image_url": "images/"+page.image_path,
                "ocr_status": page.ocr_status,
                # "processed_at": page.processed_at,
                "created_at": page.created_at,
                "updated_at": page.updated_at
            })
        
        # 按页码排序
        pages_data.sort(key=lambda x: x["page_number"])
        
        # 构建响应数据
        return {
            "file_id": file_id,
            "original_filename": pdf_doc.original_filename,
            "file_path": file_path,
            "file_exists": file_exists,
            "status": pdf_doc.status.value,
            "total_pages": pdf_doc.total_pages,
            "images_count": len(pages_data),
            "pages": pages_data,
            "pages_count": len(pages_data),
            "created_at": pdf_doc.created_at,
            "updated_at": pdf_doc.updated_at
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取PDF文件信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取文件信息失败")

@router.get("/{file_id}/image/{page_number}")
async def get_pdf_image(file_id: str, page_number: int, db: Session = Depends(get_db)):
    """
    获取PDF指定页的图片
    
    通过文件ID和页码返回对应的图片
    
    - **file_id**: PDF文件ID
    - **page_number**: 页码（从1开始）
    """
    try:
        # 获取PDF文档信息
        pdf_doc = get_pdf_document(db, file_id)
        if not pdf_doc:
            raise HTTPException(status_code=404, detail="文件不存在")
        
        # 验证页码有效性
        if page_number < 1 or page_number > pdf_doc.total_pages:
            raise HTTPException(
                status_code=400, 
                detail=f"页码无效，有效范围是1-{pdf_doc.total_pages}"
            )
        
        # 构建图片文件名和路径
        image_filename = f"p_{page_number}.png"
        image_dir = os.path.join("images", file_id)
        image_path = os.path.join(image_dir, image_filename)
        
        # 检查图片是否存在
        if not os.path.exists(image_path):
            # 尝试查找可能存在的图片文件（处理可能的命名差异）
            found = False
            if os.path.exists(image_dir) and os.path.isdir(image_dir):
                for filename in os.listdir(image_dir):
                    if filename.endswith(f"_p_{page_number}.png"):
                        image_path = os.path.join(image_dir, filename)
                        found = True
                        break
            
            if not found:
                raise HTTPException(
                    status_code=404, 
                    detail=f"第{page_number}页的图片不存在"
                )
        
        # 返回图片文件
        return FileResponse(
            path=image_path,
            filename=image_filename,
            media_type="image/png"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取PDF图片失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取图片失败")

def process_pdf_background(file_id: str, file_path: str):
    """
    后台处理PDF的函数
    """
    db = next(get_db())
    try:
        process_pdf(db, file_id, file_path)
    finally:
        db.close()

def ali_ocr(encoded_image: str):
    client = OpenAI(
        api_key = os.getenv("DASHSCOPE_API_KEY"),
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
    )

    # 构建请求体
    completion = client.chat.completions.create(
        model="qwen3-vl-plus",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{encoded_image}"
                        },
                    },
                    {"type": "text", "text": "ocr识别，直接返回识别内容"},
                ],
            },
        ],
        stream=False,
        # enable_thinking 参数开启思考过程，thinking_budget 参数设置最大推理过程 Token 数
        extra_body={
            'enable_thinking': False,
            "thinking_budget": 81920
        },
    )
    
    # 处理Ollama的流式响应（每行一个JSON对象）
    recognized_text = ""
    try:
        # 分割响应文本为多行
        # 逐行解析JSON
        for choice in completion.choices:
            logger.info(f"Ollama返回choice: {choice}")
            if not choice.message:
                print("\nUsage:")
                print(choice.message)
            else:
                try:
                    content = choice.message.content
                    # 累加识别的文本
                    recognized_text += content
                except json.JSONDecodeError:
                    logger.warning(f"无法解析JSON行: {line}")
        
        # 如果没有提取到文本，尝试直接解析整个响应（处理非流式情况）
        if not recognized_text:
            try:
                logger.info(f"尝试整体解析，获取到文本: {recognized_text}")
            except json.JSONDecodeError:
                logger.error("整体解析JSON也失败了")
                raise HTTPException(
                    status_code=503,
                    detail="OCR服务返回格式错误，无法解析响应"
                )
                
    except Exception as e:
        logger.error(f"处理Ollama响应时发生错误: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail=f"处理OCR响应失败: {str(e)}"
        )

    return recognized_text


def ollama_ocr(encoded_image: str):
    '''
    TODO: 实现ollama ocr
    '''
    from ollama import Client

    client = Client(host='http://localhost:11434')

    completion = client.generate(
        #model = 'deepseek-ocr',
        model = 'qwen3-vl:2b',
        # model = 'gemma3',
        prompt = '识别图片文字，输出markdown格式',
        images = [f"{encoded_image}"],
        stream = False,
        think = False
    )

    return completion["response"]

def easy_ocr(image: str):
    '''
    TODO: 实现ollama ocr
    '''
    import easyocr

    reader = easyocr.Reader(['ch_sim','en'])
    logger.info(f"easyocr识别图片: {image}")
    result = reader.readtext(image, detail=0)

    return "\n".join(result)


@router.post("/{file_id}/noocr/{page_number}")
async def perform_ocr_on_page(file_id: str, page_number: int, db: Session = Depends(get_db)):
    """
    标记为无需ocr
    """
    try:
        # 从数据库中更新页面的OCR结果
        from app.database.models import PDFPage

        # 获取PDF文档信息
        pdf_doc = get_pdf_document(db, file_id)
        if not pdf_doc:
            raise HTTPException(status_code=404, detail="文件不存在")

        # 查询现有页面记录
        page = db.query(PDFPage).filter(
            PDFPage.document_id == file_id,
            PDFPage.page_number == page_number
        ).first()

        page.ocr_status = True
        # page.updated_at = datetime.now()

        db.commit()
        return {"message": f"执行成功"}

    except Exception as e:
        db.rollback()
        logger.error(f"OCR识别失败: {str(e)}")
        raise HTTPException(status_code=500, detail="OCR识别过程中发生错误")


from pydantic import BaseModel
class OcrItem(BaseModel):
    again: bool = False

@router.post("/{file_id}/ocr/{page_number}")
async def perform_ocr_on_page(file_id: str, page_number: int, item: OcrItem, db: Session = Depends(get_db)):
    """
    对PDF指定页执行OCR识别
    
    使用本地ollama接口和deepseek-ocr模型进行OCR识别
    
    - **file_id**: PDF文件ID
    - **page_number**: 页码（从1开始）
    """
    try:
        # 从数据库中更新页面的OCR结果
        from app.database.models import PDFPage, ProcessingStatus
        from datetime import datetime

        # 获取PDF文档信息
        pdf_doc = get_pdf_document(db, file_id)
        if not pdf_doc:
            raise HTTPException(status_code=404, detail="文件不存在")

        # 查询现有页面记录
        page = db.query(PDFPage).filter(
            PDFPage.document_id == file_id,
            PDFPage.page_number == page_number
        ).first()

        logger.info(item)

        # 如果已经ocr，不需要再执行
        if page.ocr_status and not item.again:
            raise HTTPException(
                status_code=400, 
                detail=f"第{page_number}页已被处理"
            )
        
        # 验证页码有效性
        if page_number < 1 or page_number > pdf_doc.total_pages:
            raise HTTPException(
                status_code=400, 
                detail=f"页码无效，有效范围是1-{pdf_doc.total_pages}"
            )
        
        # 构建图片文件名和路径
        image_filename = f"p_{page_number}.png"
        image_dir = os.path.join("images", file_id)
        image_path = os.path.join(image_dir, image_filename)
        
        # 检查图片是否存在
        if not os.path.exists(image_path):
            # 尝试查找可能存在的图片文件（处理可能的命名差异）
            found = False
            if os.path.exists(image_dir) and os.path.isdir(image_dir):
                for filename in os.listdir(image_dir):
                    if filename.endswith(f"_p_{page_number}.png"):
                        image_path = os.path.join(image_dir, filename)
                        found = True
                        break
            
            if not found:
                raise HTTPException(
                    status_code=404, 
                    detail=f"第{page_number}页的图片不存在"
                )
        
        # 读取图片并转换为base64
        with open(image_path, "rb") as image_file:
            encoded_image = base64.b64encode(image_file.read()).decode("utf-8")
        
        # 调用ollama接口
        try:
            # 配置Ollama API URL
            #ollama_url = os.getenv("OLLAMA_URL", "http://192.168.18.53:11434/api/generate")
            # 初始化OpenAI客户端
            # recognized_text = easy_ocr(image_path)
            recognized_text = ali_ocr(encoded_image)
            # recognized_text = ollama_ocr(encoded_image)
                
            # 确保识别文本不为空
            if not recognized_text.strip():
                logger.warning("OCR识别结果为空")
            
            try:
                
                if page:
                    # 更新已存在的页面记录
                    page.ocr_text = recognized_text
                    page.ocr_status = True
                    page.processed_at = datetime.now()
                    logger.info(f"准备更新页面 {page_number} 的OCR结果")
                else:
                    # 创建新的页面记录
                    new_page = PDFPage(
                        document_id=file_id,
                        page_number=page_number,
                        ocr_text=recognized_text,
                        ocr_status=True,
                        processed_at=datetime.now()
                    )
                    db.add(new_page)
                    logger.info(f"准备创建页面 {page_number} 的OCR记录")
                
                # 检查是否所有页面都已完成OCR
                total_pages = pdf_doc.total_pages
                processed_pages = db.query(PDFPage).filter(
                    PDFPage.document_id == file_id,
                    PDFPage.ocr_status == True
                ).count()
                
                # 如果所有页面都已处理，更新文档状态
                if processed_pages >= total_pages:
                    pdf_doc.status = ProcessingStatus.OCR_COMPLETED
                    logger.info(f"文档 {file_id} 所有页面OCR已完成")
                elif pdf_doc.status != ProcessingStatus.PROCESSING:
                    # 如果还有页面未处理，确保状态为处理中
                    pdf_doc.status = ProcessingStatus.PROCESSING
                    logger.info(f"文档 {file_id} 更新为处理中状态")
                
                # 提交事务
                db.commit()
                logger.info(f"成功保存页面 {page_number} 的OCR结果到数据库")
                logger.info(f"当前文档进度: {processed_pages}/{total_pages} 页已完成OCR")
                
            except Exception as e:
                # 发生错误时回滚事务
                db.rollback()
                logger.error(f"保存OCR结果到数据库失败: {str(e)}")
                # 重新抛出异常，让上层处理
                raise
            
            # 返回OCR结果
            return {
                "file_id": file_id,
                "page_number": page_number,
                "original_filename": pdf_doc.original_filename,
                "recognized_text": recognized_text,
                "status": "success",
                "message": "OCR识别成功"
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"OLLAMA API调用异常: {str(e)}")
            raise HTTPException(
                status_code=503,
                detail=f"OCR服务连接失败: {str(e)}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"OCR识别失败: {str(e)}")
        raise HTTPException(status_code=500, detail="OCR识别过程中发生错误")