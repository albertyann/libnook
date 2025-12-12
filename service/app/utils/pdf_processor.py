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
                'metadata': extract_pdf_metadata(reader.metadata)
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

def extract_pdf_metadata(meta):
    """
    读取并打印PDF文件的元数据
    """
    import re
    from datetime import datetime

    logger.info(f"PDF元数据: {meta}")

    # 构建元数据字典
    # 如果 meta 为 None，则所有标准字段设为 None
    def safe_get(key, default='N/A'):
        if meta and key in meta:
            value = meta[key]
            # 尝试清理字符串（去除可能的空字节等不可见字符）
            if isinstance(value, str):
                value = value.replace('\x00', '').strip()
            return value
        return default

    # 提取信息
    info = {
        "title": safe_get("/Title"),
        "author": safe_get("/Author"),
        "creator": safe_get("/Creator"),      # 对应 "Microsoft Office Word"
        "producer": safe_get("/Producer"),    # 对应 "Aspose.Words for Java..."
        "subject": safe_get("/Subject"),
        "keywords": safe_get("/Keywords"),
        "creation_date_raw": safe_get("/CreationDate"), # 原始格式: D:2019...
        "mod_date_raw": safe_get("/ModDate"),           # 原始格式: D:2025...
    }

    # --- 日期格式转换 (可选) ---
    # 你的数据中包含时区信息 (+08'00' 或 Z)，这里提供一个简单的清洗函数
    def parse_pdf_date(pdf_str):
        if pdf_str in ['N/A', None]:
            return None
        # 移除 'D:' 前缀
        cleaned = re.sub(r'^D:', '', pdf_str)
        # 移除时区部分中的单引号 (PDF标准中时区是 +HH'mm'，Python无法直接解析单引号)
        # 简单处理：截取到秒为止 (前14位)，或者替换 ' 为 :
        # 这里采用截取前14位 (YYYYMMDDHHMMSS) 的方式，忽略时区仅做展示
        if len(cleaned) >= 14:
            try:
                # 只取年月日时分秒
                date_part = cleaned[:14]
                return datetime.strptime(date_part, "%Y%m%d%H%M%S")
            except ValueError:
                return pdf_str # 如果解析失败，返回原始字符串
        return pdf_str

    info["creation_date"] = parse_pdf_date(info["creation_date_raw"])
    info["mod_date"] = parse_pdf_date(info["mod_date_raw"])

    # 添加非元数据字段的文档信息
    # info["page_count"] = len(reader.pages)

    return info