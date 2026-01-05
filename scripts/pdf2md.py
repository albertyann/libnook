import os
import json
import hashlib
import requests
import fitz  # PyMuPDF
from PIL import Image
import io
import re
import shutil
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('pdf_to_md.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class PDFToMarkdownConverter:
    def __init__(self, 
                 lmstudio_url: str = "http://127.0.0.1:8899/v1/chat/completions",
                 model: str = "local-model",
                 dpi: int = 300,
                 temp_dir: str = "temp_images"):
        """
        初始化PDF转Markdown转换器
        
        Args:
            lmstudio_url: LM Studio API地址
            model: 使用的模型名称
            dpi: PDF转图片的DPI
            temp_dir: 临时图片目录
        """
        self.lmstudio_url = lmstudio_url
        self.model = model
        self.dpi = dpi
        self.temp_dir = Path(temp_dir)
        self.progress_file = Path("ocr_progress.json")
        self.temp_dir.mkdir(exist_ok=True)
        
    def calculate_pdf_hash(self, pdf_path: str) -> str:
        """计算PDF文件的哈希值，用于标识唯一性"""
        with open(pdf_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    
    def load_progress(self, pdf_hash: str) -> Dict:
        """加载处理进度"""
        if self.progress_file.exists():
            try:
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    progress = json.load(f)
                    return progress.get(pdf_hash, {"processed_pages": [], "ocr_texts": {}})
            except Exception as e:
                logger.error(f"加载进度文件失败: {e}")
        return {"processed_pages": [], "ocr_texts": {}}
    
    def save_progress(self, pdf_hash: str, progress: Dict):
        """保存处理进度"""
        try:
            if self.progress_file.exists():
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    all_progress = json.load(f)
            else:
                all_progress = {}
            
            all_progress[pdf_hash] = progress
            
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(all_progress, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存进度文件失败: {e}")
    
    def pdf_to_images(self, pdf_path: str, pdf_hash: str) -> List[str]:
        """将PDF转换为图片"""
        pdf_document = fitz.open(pdf_path)
        total_pages = len(pdf_document)
        image_paths = []
        
        logger.info(f"开始转换PDF为图片，共{total_pages}页")
        
        for page_num in range(total_pages):
            image_path = self.temp_dir / f"{pdf_hash}_page_{page_num + 1}.png"
            image_paths.append(str(image_path))
            
            # 如果图片已存在，跳过转换
            if image_path.exists():
                logger.info(f"第{page_num + 1}页图片已存在，跳过")
                continue
            
            page = pdf_document.load_page(page_num)
            mat = fitz.Matrix(self.dpi / 72, self.dpi / 72)
            pix = page.get_pixmap(matrix=mat)
            
            # 保存图片
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))
            img.save(image_path, "PNG", dpi=(self.dpi, self.dpi))
            logger.info(f"已转换第{page_num + 1}页为图片")
        
        pdf_document.close()
        return image_paths
    
    def image_to_base64(self, image_path: str) -> str:
        """将图片转换为base64字符串"""
        import base64
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    def ocr_with_lmstudio(self, image_path: str) -> str:
        """使用LM Studio进行OCR识别"""
        try:
            # 将图片转换为base64
            image_base64 = self.image_to_base64(image_path)
            
            # 构建请求数据
            messages = [
                {
                    "role": "system",
                    "content": """你是一个专业的OCR识别助手。请识别图片中的所有文字内容，并遵循以下规则：
1. 准确识别所有文字，保持原文格式
2. 移除页眉、页脚、页码等无关信息
3. 保留标题、段落、列表等结构
4. 如果遇到表格，用Markdown表格格式表示
5. 数学公式用LaTeX格式表示
6. 代码块用Markdown代码块格式表示
返回纯文本内容，不要添加额外说明。"""
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_base64}"
                            }
                        },
                        {
                            "type": "text",
                            "text": "请识别这张图片中的文字，并移除页眉页脚等无关信息。"
                        }
                    ]
                }
            ]
            
            payload = {
                "model": self.model,
                "messages": messages,
                "max_tokens": 4000,
                "temperature": 0.1
            }
            
            logger.info(f"发送OCR请求: {image_path}")
            response = requests.post(
                self.lmstudio_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=300
            )
            
            if response.status_code == 200:
                result = response.json()
                print(result)
                text = result['choices'][0]['message']['content']
                logger.info(f"OCR完成: {image_path}")
                return text
            else:
                logger.error(f"OCR请求失败: {response.status_code}, {response.text}")
                return ""
                
        except requests.exceptions.ConnectionError:
            logger.error(f"无法连接到LM Studio，请确保LM Studio已启动并监听{self.lmstudio_url}")
            return ""
        except Exception as e:
            logger.error(f"OCR处理出错: {e}")
            return ""
    
    def clean_text(self, text: str) -> str:
        """清理文本，移除页眉页脚等"""
        if not text:
            return ""
        
        # 分割成行
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # 跳过明显的页码（如 "1"、"2" 或 "第1页"）
            if re.match(r'^\s*\d+\s*$', line) or re.match(r'^\s*第\s*\d+\s*页\s*$', line):
                continue
            
            # 跳过常见的页眉页脚标记
            skip_patterns = [
                r'^https?://',  # URL
                r'^版权所有',  # 版权声明
                r'^©',  # 版权符号
                r'^机密',  # 机密标记
                r'^内部资料',  # 内部资料标记
            ]
            
            if any(re.match(pattern, line.strip()) for pattern in skip_patterns):
                continue
            
            # 移除行首行尾的空格
            line = line.strip()
            if line:
                cleaned_lines.append(line)
        
        # 重新组合
        cleaned_text = '\n'.join(cleaned_lines)
        
        # 移除过多的空行（保留最多2个连续空行）
        cleaned_text = re.sub(r'\n{3,}', '\n\n', cleaned_text)
        
        return cleaned_text
    
    def convert_to_markdown(self, ocr_texts: Dict[int, str]) -> str:
        """将OCR文本转换为Markdown格式"""
        markdown_content = []
        
        for page_num in sorted(ocr_texts.keys()):
            text = ocr_texts[page_num]
            if text:
                # 添加页面分隔符（可选）
                if page_num > 1:
                    markdown_content.append(f"\n--- 第 {page_num} 页 ---\n")
                
                # 清理文本
                cleaned_text = self.clean_text(text)
                markdown_content.append(cleaned_text)
        
        return '\n'.join(markdown_content)
    
    def process_pdf(self, pdf_path: str, output_dir: str = "output") -> Tuple[bool, str]:
        """处理PDF文件的主函数"""
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            logger.error(f"PDF文件不存在: {pdf_path}")
            return False, ""
        
        # 计算PDF哈希值
        pdf_hash = self.calculate_pdf_hash(str(pdf_path))
        logger.info(f"PDF哈希值: {pdf_hash}")
        
        # 加载进度
        progress = self.load_progress(pdf_hash)
        processed_pages = progress.get("processed_pages", [])
        ocr_texts = progress.get("ocr_texts", {})
        
        # 转换PDF为图片
        image_paths = self.pdf_to_images(str(pdf_path), pdf_hash)
        
        # OCR处理
        total_pages = len(image_paths)
        for page_num, image_path in enumerate(image_paths, 1):
            # 如果已经处理过，跳过
            if page_num in processed_pages:
                logger.info(f"第{page_num}页已处理，跳过")
                continue
            
            logger.info(f"开始处理第{page_num}/{total_pages}页")
            ocr_text = self.ocr_with_lmstudio(image_path)
            
            if ocr_text:
                ocr_texts[page_num] = ocr_text
                processed_pages.append(page_num)
                
                # 保存进度
                progress = {
                    "pdf_name": pdf_path.name,
                    "processed_pages": processed_pages,
                    "ocr_texts": ocr_texts,
                    "last_updated": datetime.now().isoformat()
                }
                self.save_progress(pdf_hash, progress)
                logger.info(f"第{page_num}页处理完成并保存进度")
            else:
                logger.warning(f"第{page_num}页OCR失败")
        
        # 转换为Markdown
        if ocr_texts:
            markdown_content = self.convert_to_markdown(ocr_texts)
            
            # 保存Markdown文件
            output_dir = Path(output_dir)
            output_dir.mkdir(exist_ok=True)
            
            output_path = output_dir / f"{pdf_path.stem}.md"
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            logger.info(f"Markdown文件已保存: {output_path}")
            
            # 清理临时文件
            self.cleanup_temp_files(pdf_hash)
            
            return True, str(output_path)
        else:
            logger.error("未成功OCR任何页面")
            return False, ""
    
    def cleanup_temp_files(self, pdf_hash: str):
        """清理临时文件"""
        try:
            # 删除该PDF对应的临时图片
            for img_file in self.temp_dir.glob(f"{pdf_hash}_page_*.png"):
                img_file.unlink()
                logger.info(f"已删除临时文件: {img_file}")
            
            # 如果临时目录为空，删除目录
            if not any(self.temp_dir.iterdir()):
                self.temp_dir.rmdir()
                
        except Exception as e:
            logger.error(f"清理临时文件失败: {e}")
    
    def cleanup_all(self):
        """清理所有临时文件和进度文件"""
        try:
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
                logger.info(f"已删除临时目录: {self.temp_dir}")
            
            if self.progress_file.exists():
                self.progress_file.unlink()
                logger.info(f"已删除进度文件: {self.progress_file}")
                
        except Exception as e:
            logger.error(f"清理失败: {e}")

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="PDF转Markdown工具")
    parser.add_argument("pdf_file", help="输入的PDF文件路径")
    parser.add_argument("-o", "--output", default="output", help="输出目录")
    parser.add_argument("--lmstudio-url", default="http://127.0.0.1:8899/v1/chat/completions", 
                       help="LM Studio API地址")
    parser.add_argument("--model", default="local-model", help="模型名称")
    parser.add_argument("--cleanup", action="store_true", help="清理所有临时文件")
    
    args = parser.parse_args()
    
    converter = PDFToMarkdownConverter(
        lmstudio_url=args.lmstudio_url,
        model=args.model
    )
    
    if args.cleanup:
        converter.cleanup_all()
        logger.info("已清理所有临时文件")
        return
    
    success, output_path = converter.process_pdf(args.pdf_file, args.output)
    
    if success:
        logger.info(f"处理完成！Markdown文件保存在: {output_path}")
    else:
        logger.error("处理失败，请检查日志")

if __name__ == "__main__":
    main()