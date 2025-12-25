import os
from typing import List, Optional, Dict, Any
import logging
from PIL import Image

# 尝试导入PyMuPDF (fitz)
HAS_PYMUPDF = False
try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    logger.warning("PyMuPDF库未安装，请安装: pip install PyMuPDF")

# 尝试导入PyPDF2作为备用
HAS_PYPDF2 = False
try:
    import PyPDF2
    HAS_PYPDF2 = True
except ImportError:
    logger.warning("PyPDF2库未安装，无法使用备用PDF处理方法")

logger = logging.getLogger(__name__)

def pdf_to_images(pdf_path: str, output_dir: str, dpi: int = 300) -> List[str]:
    """
    将PDF文件的每一页转换为图片
    :param pdf_path: PDF文件路径
    :param output_dir: 输出图片目录
    :param dpi: 图片分辨率 (PyMuPDF使用zoom参数，这里进行换算)
    :return: 生成的图片文件路径列表
    """
    try:
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 检查PDF文件是否存在
        if not os.path.exists(pdf_path):
            error_msg = f"PDF文件不存在: {pdf_path}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)
        
        # 如果PyMuPDF可用，则使用它进行转换
        if HAS_PYMUPDF:
            # 打开PDF文档
            pdf_document = fitz.open(pdf_path)
            pdf_filename = os.path.splitext(os.path.basename(pdf_path))[0]
            image_paths = []
            
            # 计算缩放因子，PyMuPDF的默认DPI约为72
            zoom = dpi / 72.0
            matrix = fitz.Matrix(zoom, zoom)
            
            logger.info(f"开始使用PyMuPDF转换PDF为图片: {pdf_path}, 总页数: {len(pdf_document)}")
            
            # 遍历每一页
            for page_number in range(len(pdf_document)):
                # 获取页面
                page = pdf_document[page_number]
                
                # 将页面转换为图片
                pix = page.get_pixmap(matrix=matrix)
                
                # 构造图片文件名
                image_filename = f"p_{page_number + 1}.png"
                image_path = os.path.join(output_dir, image_filename)
                
                # 保存图片
                pix.save(image_path)
                image_paths.append(image_path)
                logger.info(f"生成图片: {image_path}")
            
            # 关闭PDF文档
            pdf_document.close()
            
            logger.info(f"PDF转换完成: {pdf_path}, 生成了 {len(image_paths)} 张图片")
            return image_paths
        else:
            # 如果PyMuPDF不可用，但PyPDF2可用，尝试获取基本信息
            if HAS_PYPDF2:
                logger.info("PyMuPDF不可用，将使用PyPDF2获取PDF基本信息作为备用")
                pdf_info = get_pdf_info_using_pypdf2(pdf_path)
                logger.info(f"PDF信息: {pdf_info}")
                return []
            raise RuntimeError("PyMuPDF和PyPDF2均不可用，无法处理PDF文件")
    
    except Exception as e:
        logger.error(f"PDF处理失败: {pdf_path}, 错误: {str(e)}")
        raise

def get_pdf_info_using_pypdf2(pdf_path: str) -> Dict[str, Any]:
    """
    使用PyPDF2获取PDF的基本信息
    :param pdf_path: PDF文件路径
    :return: 包含PDF信息的字典
    """
    if not HAS_PYPDF2:
        raise ImportError("PyPDF2库未安装")
    
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            info = {
                'total_pages': len(reader.pages),
                'metadata': reader.metadata
            }
            return info
    except Exception as e:
        logger.error(f"使用PyPDF2获取PDF信息失败: {pdf_path}, 错误: {str(e)}")
        raise

def optimize_image(image_path: str, max_width: int = None, max_height: int = None, quality: int = 95) -> str:
    """
    优化图片大小和质量
    :param image_path: 图片路径
    :param max_width: 最大宽度
    :param max_height: 最大高度
    :param quality: 图片质量
    :return: 优化后的图片路径
    """
    try:
        with Image.open(image_path) as img:
            # 调整大小
            if max_width or max_height:
                width, height = img.size
                new_size = (width, height)
                
                if max_width and width > max_width:
                    ratio = max_width / width
                    new_size = (max_width, int(height * ratio))
                
                if max_height and new_size[1] > max_height:
                    ratio = max_height / new_size[1]
                    new_size = (int(new_size[0] * ratio), max_height)
                
                if new_size != (width, height):
                    img = img.resize(new_size, Image.LANCZOS)
            
            # 保存优化后的图片
            img.save(image_path, 'PNG', quality=quality)
            logger.info(f"图片优化完成: {image_path}")
        
        return image_path
    
    except Exception as e:
        logger.error(f"图片优化失败: {image_path}, 错误: {str(e)}")
        raise