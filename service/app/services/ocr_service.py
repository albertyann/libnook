import requests
import os
import logging
import base64
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

logger = logging.getLogger(__name__)

class OCRService:
    """
    OCR服务类，用于调用远程OCR API
    """
    
    def __init__(self):
        self.api_url = os.getenv("OCR_API_URL", "https://api.example.com/ocr")
        self.api_key = os.getenv("OCR_API_KEY", "")
        self.timeout = 30  # 30秒超时
    
    def recognize_image(self, image_path: str) -> Optional[str]:
        """
        识别图片中的文字
        :param image_path: 图片路径
        :return: 识别出的文本，如果失败返回None
        """
        try:
            # 读取图片文件
            with open(image_path, 'rb') as image_file:
                image_data = image_file.read()
            
            # 准备请求数据
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            # 将图片转换为base64编码
            base64_image = base64.b64encode(image_data).decode('utf-8')
            
            payload = {
                "image": base64_image,
                "language": "auto",  # 自动检测语言
                "model": "document"  # 使用文档识别模型
            }
            
            # 发送请求
            logger.info(f"调用OCR API识别图片: {image_path}")
            response = requests.post(
                self.api_url,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            
            # 检查响应
            if response.status_code == 200:
                result = response.json()
                # 假设API返回的文本在'result'字段中
                recognized_text = result.get('text', '') or result.get('result', '')
                logger.info(f"OCR识别成功: {image_path}, 文本长度: {len(recognized_text)}")
                return recognized_text
            else:
                logger.error(f"OCR API返回错误: 状态码={response.status_code}, 响应={response.text}")
                return None
        
        except requests.exceptions.Timeout:
            logger.error(f"OCR API请求超时: {image_path}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"OCR API请求失败: {image_path}, 错误: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"OCR识别异常: {image_path}, 错误: {str(e)}")
            return None

# 创建OCR服务实例
ocr_service = OCRService()

def perform_ocr_on_image(image_path: str) -> Optional[str]:
    """
    对图片执行OCR识别的便捷函数
    """
    return ocr_service.recognize_image(image_path)