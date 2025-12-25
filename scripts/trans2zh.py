import re
import json
import time
import requests
from pathlib import Path
from typing import List, Dict, Optional
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MarkdownTranslator:
    def __init__(self, api_url: str = "http://127.0.0.1:8899/v1/chat/completions"):
        """
        初始化翻译器
        
        Args:
            api_url: LM Studio API地址
        """
        self.api_url = api_url
        self.headers = {
            "Content-Type": "application/json"
        }
        
    def split_markdown(self, content: str) -> List[Dict]:
        """
        将Markdown内容拆分成逻辑段落
        
        Args:
            content: Markdown内容
            
        Returns:
            段落列表，每个段落包含文本和类型信息
        """
        paragraphs = []
        
        # 按空行分割
        raw_blocks = re.split(r'\n--- 第.*页 ---\n', content.strip())
        
        for block in raw_blocks:
            block = block.strip()
            if not block:
                continue
                
            # 判断段落类型
            paragraph_type = "text"
            if block.startswith('#'):
                paragraph_type = "heading"
            elif block.startswith('```'):
                paragraph_type = "code"
            elif re.match(r'^[-*+]\s', block, re.MULTILINE):
                paragraph_type = "list"
            elif re.match(r'^\d+\.\s', block, re.MULTILINE):
                paragraph_type = "numbered_list"
            elif re.match(r'^>', block, re.MULTILINE):
                paragraph_type = "blockquote"
            elif re.match(r'^\|', block, re.MULTILINE):
                paragraph_type = "table"
                
            paragraphs.append({
                "text": block,
                "type": paragraph_type
            })
            
        return paragraphs
    
    def translate_text(self, text: str, max_retries: int = 3) -> Optional[str]:
        """
        调用LM Studio API翻译文本
        
        Args:
            text: 要翻译的文本
            max_retries: 最大重试次数
            
        Returns:
            翻译后的文本，失败时返回None
        """
        # 构建提示词
        prompt = f"""请将以下文本翻译成中文，保持格式不变，仅返回翻译结果：

{text}

翻译结果："""
        
        payload = {
            "model": "qwen3-vl-8b",  # LM Studio中的模型名称
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 2000,
            "stream": False
        }
        
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    self.api_url, 
                    headers=self.headers, 
                    data=json.dumps(payload),
                    timeout=60
                )
                
                if response.status_code == 200:
                    result = response.json()
                    translation = result["choices"][0]["message"]["content"].strip()
                    return translation
                else:
                    logger.warning(f"API请求失败: {response.status_code}, 尝试 {attempt + 1}/{max_retries}")
                    
            except requests.exceptions.RequestException as e:
                logger.warning(f"请求异常: {e}, 尝试 {attempt + 1}/{max_retries}")
            
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # 指数退避
            
        logger.error(f"翻译失败: {text[:50]}...")
        return None
    
    def translate_paragraph(self, paragraph: Dict) -> Dict:
        """
        翻译单个段落
        
        Args:
            paragraph: 段落字典
            
        Returns:
            包含原文和译文的段落字典
        """
        text = paragraph["text"]
        para_type = paragraph["type"]
        
        # 不需要翻译的段落类型
        if para_type in ["code"]:
            return {
                "original": text,
                "translated": text,  # 代码块不翻译
                "type": para_type,
                "skip_translation": True
            }
        
        # 翻译段落
        translated = self.translate_text(text)
        
        if translated is None:
            # 翻译失败时返回原文
            translated = text
            
        return {
            "original": text,
            "translated": translated,
            "type": para_type,
            "skip_translation": False
        }
    
    def create_bilingual_markdown(self, paragraphs: List[Dict], output_path: str):
        """
        创建双语对照的Markdown文件
        
        Args:
            paragraphs: 包含原文和译文的段落列表
            output_path: 输出文件路径
        """
        bilingual_content = []
        
        for i, para in enumerate(paragraphs, 1):
            original = para["original"]
            translated = para["translated"]
            para_type = para["type"]
            
            # 添加分隔符
            bilingual_content.append(f"<!-- Paragraph {i} -->")
            
            # 根据段落类型处理
            if para_type == "code":
                # 代码块直接复制
                bilingual_content.append(original)
            elif para_type == "heading":
                # 标题：原文在上，译文在下
                bilingual_content.append(original)
                bilingual_content.append("")
                bilingual_content.append(f"_{translated}_")
            elif para_type == "table":
                # 表格：保持原样
                bilingual_content.append(original)
                bilingual_content.append("")
                bilingual_content.append(f"*表: {translated}*")
            else:
                # 普通文本：双语对照
                bilingual_content.append(original)
                bilingual_content.append("")
                bilingual_content.append(f"> {translated}")
            
            bilingual_content.append("")  # 段落间空行
        
        # 写入文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(bilingual_content))
        
        logger.info(f"双语文件已保存: {output_path}")
    
    def translate_markdown_file(self, input_path: str, output_path: Optional[str] = None):
        """
        主函数：翻译Markdown文件
        
        Args:
            input_path: 输入文件路径
            output_path: 输出文件路径（可选）
        """
        # 检查输入文件
        input_file = Path(input_path)
        if not input_file.exists():
            logger.error(f"输入文件不存在: {input_path}")
            return
        
        # 生成输出路径
        if output_path is None:
            output_file = input_file.parent / f"{input_file.stem}_bilingual{input_file.suffix}"
            output_path = str(output_file)
        
        # 读取文件
        logger.info(f"正在读取文件: {input_path}")
        with open(input_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 拆分段落
        logger.info("正在拆分Markdown段落...")
        paragraphs = self.split_markdown(content)
        logger.info(f"共拆分成 {len(paragraphs)} 个段落")
        
        # 翻译每个段落
        translated_paragraphs = []
        for i, para in enumerate(paragraphs, 1):
            logger.info(f"正在翻译段落 {i}/{len(paragraphs)}...")
            translated = self.translate_paragraph(para)
            translated_paragraphs.append(translated)
            
            # 避免请求过快
            time.sleep(0.5)
        
        # 创建双语文件
        logger.info("正在生成双语对照文件...")
        self.create_bilingual_markdown(translated_paragraphs, output_path)
        
        # 统计信息
        translated_count = len([p for p in translated_paragraphs if not p.get("skip_translation", False)])
        logger.info(f"翻译完成！共处理 {len(translated_paragraphs)} 个段落，其中 {translated_count} 个已翻译")

def main():
    """
    主函数：从命令行获取输入
    """
    import argparse
    
    parser = argparse.ArgumentParser(description="Markdown文件双语翻译工具")
    parser.add_argument("input", help="输入的Markdown文件路径")
    parser.add_argument("-o", "--output", help="输出的双语文件路径（可选）")
    parser.add_argument("--api", default="http://127.0.0.1:8899/v1/chat/completions", 
                       help="LM Studio API地址（默认: http://127.0.0.1:8899/v1/chat/completions）")
    
    args = parser.parse_args()
    
    # 创建翻译器
    translator = MarkdownTranslator(api_url=args.api)
    
    # 测试API连接
    logger.info("测试API连接...")
    try:
        test_response = requests.get(args.api.replace("/v1/chat/completions", "/v1/models"), timeout=5)
        if test_response.status_code == 200:
            logger.info("API连接成功")
        else:
            logger.warning(f"API连接测试失败: {test_response.status_code}")
    except Exception as e:
        logger.warning(f"无法连接到API: {e}")
        logger.warning("请确保LM Studio正在运行，且端口正确（默认: 8899）")
    
    # 执行翻译
    translator.translate_markdown_file(args.input, args.output)

if __name__ == "__main__":
    main()