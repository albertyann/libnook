from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum, Boolean
from sqlalchemy.sql import func
import enum
from app.database.database import Base

# 定义处理状态枚举类
class ProcessingStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PARSED = "parsed"
    IMAGES_GENERATED = "images_generated"
    OCR_COMPLETED = "ocr_completed"
    ERROR = "error"

# PDF文档表
class PDFDocument(Base):
    __tablename__ = "pdf_documents"
    
    id = Column(String, primary_key=True, index=True)  # 使用UUID作为主键
    original_filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    pdf_type = Column(String, nullable=True)
    pdf_metadata = Column(String, nullable=True)
    total_pages = Column(Integer, default=0)
    status = Column(Enum(ProcessingStatus), default=ProcessingStatus.UPLOADED)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

# PDF页面表
class PDFPage(Base):
    __tablename__ = "pdf_pages"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    document_id = Column(String, ForeignKey("pdf_documents.id"), nullable=False)
    page_number = Column(Integer, nullable=False)
    image_path = Column(String, nullable=True)
    ocr_text = Column(Text, nullable=True)
    ocr_status = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())