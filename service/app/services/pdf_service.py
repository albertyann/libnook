from sqlalchemy.orm import Session
from app.database.models import PDFDocument, PDFPage, ProcessingStatus
from app.utils.pdf_processor import parse_pdf_info, extract_text_from_page
from app.utils.image_converter import pdf_to_images
from app.services.ocr_service import perform_ocr_on_image
import os
import logging

logger = logging.getLogger(__name__)

def create_pdf_record(db: Session, file_id: str, original_filename: str, file_path: str) -> PDFDocument:
    """
    在数据库中创建PDF记录
    """
    pdf_doc = PDFDocument(
        id=file_id,
        original_filename=original_filename,
        file_path=file_path
    )
    db.add(pdf_doc)
    db.commit()
    db.refresh(pdf_doc)
    logger.info(f"创建PDF记录: {file_id}")
    return pdf_doc

def update_pdf_status(db: Session, file_id: str, status: ProcessingStatus, error_message: str = None) -> PDFDocument:
    """
    更新PDF处理状态
    """
    pdf_doc = db.query(PDFDocument).filter(PDFDocument.id == file_id).first()
    if pdf_doc:
        pdf_doc.status = status
        if error_message:
            pdf_doc.error_message = error_message
        db.commit()
        db.refresh(pdf_doc)
        logger.info(f"更新PDF状态: {file_id} -> {status}")
    return pdf_doc

def classify_and_extract(pdf_path, threshold_per_page=20):
    """
    判断PDF类型并提取文本
    :param pdf_path: PDF文件路径
    :param threshold_per_page: 每页文本长度阈值，用于判断是否为图片型
    :return: 字典，包含类型和提取的文本（如果是文本型）
    """
    result = {
        "type": None,
        "text": "",
        "pages": []
    }

    try:
        # 1. 打开文档
        total_text_length = 0
        page_texts = []

        # 2. 遍历前20页
        for page_num in range(0, 20):
            # 提取纯文本，并去除首尾空白字符
            text = extract_text_from_page(pdf_path, page_num)
            logger.info(f"第 {page_num} 页文本长度: {text}")

            if text:
                # 统计该页文本长度
                page_texts.append(text)
                total_text_length += len(text)
        
        # 3. 计算平均值并判断类型
        len_texts = 1 if len(page_texts) == 0 else len(page_texts)
        avg_text_length = total_text_length / len_texts
        
        if avg_text_length < threshold_per_page:
            result["type"] = "image-based" # 图片型
            print(f"判定结果：图片型 PDF (平均每页文本长度: {avg_text_length:.2f})")
        else:
            result["type"] = "text-based" # 文本型
            result["text"] = "\n--- 分页符 ---\n".join(page_texts)
            result["pages"] = page_texts # 保存每页内容的列表
            print(f"判定结果：文本型 PDF (平均每页文本长度: {avg_text_length:.2f})")
            
    except Exception as e:
        print(f"处理出错: {e}")
        result["type"] = "error"
    
    return result

def process_pdf(db: Session, file_id: str, file_path: str) -> None:
    """
    处理PDF文件：解析并保存信息到数据库，然后生成图片
    """
    try:
        # 更新状态为处理中
        update_pdf_status(db, file_id, ProcessingStatus.PROCESSING)
        
        # 解析PDF信息
        pdf_info = parse_pdf_info(file_path)
        pdf_type = classify_and_extract(file_path)

        # 更新PDF文档信息
        pdf_doc = db.query(PDFDocument).filter(PDFDocument.id == file_id).first()
        if pdf_doc:
            pdf_doc.total_pages = pdf_info['total_pages']
            pdf_doc.pdf_type = pdf_type['type']
            pdf_doc.pdf_metadata = str(pdf_info['metadata'])

            logger.info(f"PDF文档 {file_id} 总页数: {pdf_info['total_pages']}")
            
            # 为每一页创建记录
            for page_number in range(pdf_info['total_pages']):
                pdf_page = PDFPage(
                    document_id = file_id,
                    page_number = page_number + 1  # 页码从1开始
                )
                db.add(pdf_page)
            
            db.commit()
            
            # 更新状态为解析完成
            update_pdf_status(db, file_id, ProcessingStatus.PARSED)
            logger.info(f"PDF解析完成: {file_id}, 页数: {pdf_info['total_pages']}")
            
            # 生成图片目录
            images_dir = os.path.join(os.getenv("IMAGES_DIR", "./images"), file_id)
            
            # 转换PDF为图片
            image_paths = pdf_to_images(file_path, images_dir)
            
            # 检查是否生成了图片
            if image_paths:
                # 更新数据库中的图片路径
                for i, image_path in enumerate(image_paths):
                    page_number = i + 1
                    pdf_page = db.query(PDFPage).filter(
                        PDFPage.document_id == file_id,
                        PDFPage.page_number == page_number
                    ).first()
                    
                    if pdf_page:
                        # 保存相对路径
                        relative_path = os.path.relpath(image_path, os.getenv("IMAGES_DIR", "./images"))
                        pdf_page.image_path = relative_path
                
                db.commit()
                
                # 更新状态为图片生成完成
                update_pdf_status(db, file_id, ProcessingStatus.IMAGES_GENERATED)
                logger.info(f"PDF图片生成完成: {file_id}, 生成了 {len(image_paths)} 张图片")
            else:
                # 如果没有生成图片，更新状态但不中断处理
                logger.warning(f"PDF图片生成失败或未生成图片: {file_id}")
                # 继续处理，但跳过OCR步骤
            
            # TODO: 实现OCR步骤
            if pdf_doc.pdf_type == "text-based":
                # 对每一页执行OCR
                for page_number in range(pdf_info['total_pages']):
                    pdf_page = db.query(PDFPage).filter(
                        PDFPage.document_id == file_id,
                        PDFPage.page_number == page_number + 1
                    ).first()

                    logger.info(f"处理PDF页面 {page_number + 1} 进行OCR")
                    
                    if pdf_page and not pdf_page.ocr_status:
                       # 只直接将pdf转为文本并保存
                       page_text = extract_text_from_page(file_path, page_number + 1)
                       pdf_page.ocr_text = page_text
                       pdf_page.ocr_status = True
        db.commit()
    except Exception as e:
        if pdf_doc.pdf_type == "text-based":
            # 回滚数据库操作
            db.rollback()
            error_msg = f"PDF OCR处理失败: {str(e)}"
            logger.error(error_msg)
            update_pdf_status(db, file_id, ProcessingStatus.ERROR, error_msg)
        
        error_msg = f"PDF处理失败: {str(e)}"
        logger.error(error_msg)
        update_pdf_status(db, file_id, ProcessingStatus.ERROR, error_msg)

def get_pdf_document(db: Session, file_id: str) -> PDFDocument:
    """
    获取PDF文档信息
    """
    return db.query(PDFDocument).filter(PDFDocument.id == file_id).first()

def get_pdf_pages(db: Session, file_id: str) -> list[PDFPage]:
    """
    获取PDF的所有页面
    """
    return db.query(PDFPage).filter(PDFPage.document_id == file_id).order_by(PDFPage.page_number).all()