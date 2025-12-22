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


def ali_ocr(encoded_image: str):
    client = OpenAI(
        api_key = os.getenv("DASHSCOPE_API_KEY"),
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
    )

    # 构建请求体
    completion = client.chat.completions.create(
        model="qwen3-vl-plus",
        messages = [
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


def lm_studio_ocr(encoded_image: str):
    '''
    lmstudio ocr
    '''
    from openai import OpenAI

    client = OpenAI(base_url="http://localhost:8899/v1", api_key="lm-studio")

    completion = client.chat.completions.create(
        model="qwen/qwen3-vl-8b",
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{encoded_image}"
                        },
                    },
                    {"type": "text", "text": "ocr识别，忽略页眉和页脚，直接返回识别内容"},
                ],
            },
        ]
    )

    recognized_text = ""
    try:
        # 分割响应文本为多行
        # 逐行解析JSON
        for choice in completion.choices:
            logger.info(f"LmStudio 返回choice: {choice}")
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
    except Exception as e:
        logger.error(f"处理LmStudio响应时发生错误: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail=f"处理LmStudio响应失败: {str(e)}"
        )

    # 替换HTML特殊字符
    recognized_text = recognized_text.replace("<", "&lt;").replace(">", "&gt;")

    return recognized_text

def easy_ocr(image: str):
    '''
    TODO: 实现ollama ocr
    '''
    import easyocr

    reader = easyocr.Reader(['ch_sim','en'])
    logger.info(f"easyocr识别图片: {image}")
    result = reader.readtext(image, detail=0)

    return "\n".join(result)
