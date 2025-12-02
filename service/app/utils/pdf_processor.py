import PyPDF2
import logging
import os
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

def parse_pdf_info(file_path: str) -> Dict[str, Any]:
    """
    解析PDF文件，获取基本信息
    :param file_path: PDF文件路径
    :return: 包含PDF信息的字典
    """
    try:
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            
            # 获取PDF信息
            info = {
                'total_pages': len(reader.pages),
                'metadata': reader.metadata
            }
            
            logger.info(f"成功解析PDF文件: {file_path}, 页数: {info['total_pages']}")
            return info
    except Exception as e:
        logger.error(f"解析PDF文件失败: {file_path}, 错误: {str(e)}")
        raise

def extract_text_from_page(file_path: str, page_number: int) -> Optional[str]:
    """
    从指定页码提取文本
    :param file_path: PDF文件路径
    :param page_number: 页码（从0开始）
    :return: 提取的文本，如果失败返回None
    """
    try:
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            
            if page_number < 0 or page_number >= len(reader.pages):
                raise ValueError(f"页码超出范围: {page_number}")
            
            page = reader.pages[page_number]
            text = page.extract_text()
            
            return text
    except Exception as e:
        logger.error(f"提取页面文本失败: 文件={file_path}, 页码={page_number}, 错误: {str(e)}")
        return None