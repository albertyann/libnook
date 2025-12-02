from sqlalchemy.orm import Session
from app.database.models import PDFDocument, PDFPage, ProcessingStatus
from app.utils.pdf_processor import parse_pdf_info
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

def process_pdf(db: Session, file_id: str, file_path: str) -> None:
    """
    处理PDF文件：解析并保存信息到数据库，然后生成图片
    """
    try:
        # 更新状态为处理中
        update_pdf_status(db, file_id, ProcessingStatus.PROCESSING)
        
        # 解析PDF信息
        pdf_info = parse_pdf_info(file_path)
        
        # 更新PDF文档信息
        pdf_doc = db.query(PDFDocument).filter(PDFDocument.id == file_id).first()
        if pdf_doc:
            pdf_doc.total_pages = pdf_info['total_pages']
            logger.info(f"PDF文档 {file_id} 总页数: {pdf_info['total_pages']}")
            
            # 为每一页创建记录
            for page_number in range(pdf_info['total_pages']):
                pdf_page = PDFPage(
                    document_id=file_id,
                    page_number=page_number + 1  # 页码从1开始
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
            
            # 只有当有图片时才进行OCR识别
            if image_paths:
                images_base_dir = os.getenv("IMAGES_DIR", "./images")
                all_pages_processed = True
                
                for pdf_page in db.query(PDFPage).filter(PDFPage.document_id == file_id).all():
                    if pdf_page.image_path:
                        # 获取完整的图片路径
                        full_image_path = os.path.join(images_base_dir, pdf_page.image_path)
                        
                        if os.path.exists(full_image_path):
                            # 执行OCR识别
                            ocr_text = perform_ocr_on_image(full_image_path)
                            
                            if ocr_text:
                                pdf_page.ocr_text = ocr_text
                                pdf_page.ocr_status = True
                                logger.info(f"页面OCR识别完成: {file_id} - 第{pdf_page.page_number}页")
                            else:
                                all_pages_processed = False
                                logger.warning(f"页面OCR识别失败: {file_id} - 第{pdf_page.page_number}页")
                        else:
                            all_pages_processed = False
                            logger.warning(f"页面图片不存在: {file_id} - 第{pdf_page.page_number}页")
                    else:
                        all_pages_processed = False
                        logger.warning(f"页面无图片路径: {file_id} - 第{pdf_page.page_number}页")
                
                db.commit()
                
                # 如果所有页面都成功处理，更新状态
                if all_pages_processed:
                    update_pdf_status(db, file_id, ProcessingStatus.OCR_COMPLETED)
                    logger.info(f"PDF OCR识别全部完成: {file_id}")
                else:
                    logger.warning(f"PDF部分页面OCR识别失败: {file_id}")
            else:
                # 如果没有生成图片，设置状态为解析完成但无法进行OCR
                update_pdf_status(db, file_id, ProcessingStatus.PARSED)
                logger.info(f"PDF解析完成但无法生成图片，跳过OCR处理: {file_id}")
    
    except Exception as e:
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