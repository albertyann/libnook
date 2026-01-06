#!/usr/bin/env python3
"""
这是一个基于 Ollama + DeepseekOCR 的脚本
调用 远程接口，执行后处理结果
"""

from PIL import Image, ImageDraw, ImageFont, ImageOps
import requests
import base64
import json
import sys
import re
import os
from tqdm import tqdm
import numpy as np
from config import MODEL_PATH, INPUT_PATH, OUTPUT_PATH, PROMPT, SKIP_REPEAT, MAX_CONCURRENCY, NUM_WORKERS, CROP_MODE

os.environ['URLLIB3_NO_IPV6'] = '1'

OLLAMA_URI = "http://127.0.0.1:11434"

def re_match(text):
    pattern = r'(<\|ref\|>(.*?)<\|/ref\|><\|det\|>(.*?)<\|/det\|>)'
    matches = re.findall(pattern, text, re.DOTALL)

    mathes_image = []
    mathes_other = []
    for a_match in matches:
        if '<|ref|>image<|/ref|>' in a_match[0]:
            mathes_image.append(a_match[0])
        else:
            mathes_other.append(a_match[0])
    return matches, mathes_image, mathes_other

def extract_coordinates_and_label(ref_text, image_width, image_height):
    try:
        label_type = ref_text[1]
        cor_list = eval(ref_text[2])
    except Exception as e:
        print(e)
        return None

    return (label_type, cor_list)

def draw_bounding_boxes(image, refs):

    image_width, image_height = image.size
    img_draw = image.copy()
    draw = ImageDraw.Draw(img_draw)

    overlay = Image.new('RGBA', img_draw.size, (0, 0, 0, 0))
    draw2 = ImageDraw.Draw(overlay)
    
    #     except IOError:
    font = ImageFont.load_default()

    img_idx = 0
    
    for i, ref in enumerate(refs):
        try:
            result = extract_coordinates_and_label(ref, image_width, image_height)
            if result:
                label_type, points_list = result
                
                color = (np.random.randint(0, 200), np.random.randint(0, 200), np.random.randint(0, 255))

                color_a = color + (20, )
                for points in points_list:
                    x1, y1, x2, y2 = points

                    x1 = int(x1 / 999 * image_width)
                    y1 = int(y1 / 999 * image_height)

                    x2 = int(x2 / 999 * image_width)
                    y2 = int(y2 / 999 * image_height)

                    if label_type == 'image':
                        try:
                            cropped = image.crop((x1, y1, x2, y2))
                            cropped.save(f"{OUTPUT_PATH}/images/{img_idx}.jpg")
                        except Exception as e:
                            print(e)
                            pass
                        img_idx += 1
                        
                    try:
                        if label_type == 'title':
                            draw.rectangle([x1, y1, x2, y2], outline=color, width=4)
                            draw2.rectangle([x1, y1, x2, y2], fill=color_a, outline=(0, 0, 0, 0), width=1)
                        else:
                            draw.rectangle([x1, y1, x2, y2], outline=color, width=2)
                            draw2.rectangle([x1, y1, x2, y2], fill=color_a, outline=(0, 0, 0, 0), width=1)

                        text_x = x1
                        text_y = max(0, y1 - 15)
                            
                        text_bbox = draw.textbbox((0, 0), label_type, font=font)
                        text_width = text_bbox[2] - text_bbox[0]
                        text_height = text_bbox[3] - text_bbox[1]
                        draw.rectangle([text_x, text_y, text_x + text_width, text_y + text_height], 
                                    fill=(255, 255, 255, 30))
                        
                        draw.text((text_x, text_y), label_type, font=font, fill=color)
                    except:
                        pass
        except:
            continue
    img_draw.paste(overlay, (0, 0), overlay)
    return img_draw

def process_image_with_refs(image, ref_texts):
    result_image = draw_bounding_boxes(image, ref_texts)
    return result_image

def load_image(image_path):
    try:
        image = Image.open(image_path)
        corrected_image = ImageOps.exif_transpose(image)
        return corrected_image
    except Exception as e:
        print(f"error: {e}")
        try:
            return Image.open(image_path)
        except:
            return None

def document_to_markdown(image_path):
    """
    将文档图像转换为Markdown
    
    Args:
        image_path: 图像文件路径
        stream: 是否流式输出
    """
    
    # 读取并编码图像
    try:
        with open(image_path, "rb") as f:
            image_bytes = f.read()
        
        image = load_image(image_path).convert('RGB')

        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        
        # 构建请求数据
        data = {
            "model": 'deepseek-ocr',
            "prompt": "<image>\n<|grounding|>Convert the document to markdown.",
            #"prompt": "<image>\n<|grounding|>OCR this image.",
            "stream": False,
            "images": [base64_image],
            "options": {
                "temperature": 0.1,
                "num_predict": 2048
            }
        }
        
        # 发送请求
        response = requests.post(
            f"{OLLAMA_URI}/api/generate",
            json=data,
            stream=False
        )
        
        outputs = response.json()
        result_out = outputs.get('response', '')

        handle_result(result_out, image)

    except FileNotFoundError as er:
        print(f"错误: 文件未找到 - {image_path}")
    except requests.exceptions.ConnectionError:
        print("错误: 无法连接到Ollama服务")
        print("请确保Ollama服务正在运行: ollama serve")
    except Exception as e:
        print(f"错误: {e}")

def handle_result(result_out, image):
    """
    处理ocr后的结果
    """
    print('='*15 + 'save results:' + '='*15)

    image_draw = image.copy()

    outputs = result_out

    # 保存ocr之后的原始数据
    with open(f'{OUTPUT_PATH}/result_ori.mmd', 'w', encoding = 'utf-8') as afile:
        afile.write(outputs)

    # 结果匹配
    matches_ref, matches_images, mathes_other = re_match(outputs)

    result = process_image_with_refs(image_draw, matches_ref)

    for idx, a_match_image in enumerate(tqdm(matches_images, desc="image")):
        outputs = outputs.replace(a_match_image, f'![](images/' + str(idx) + '.jpg)\n')

    for idx, a_match_other in enumerate(tqdm(mathes_other, desc="other")):
        outputs = outputs.replace(a_match_other, '').replace('\\coloneqq', ':=').replace('\\eqqcolon', '=:')

    with open(f'{OUTPUT_PATH}/result.md', 'w', encoding = 'utf-8') as afile:
        afile.write(outputs)

    if 'line_type' in outputs:
        import matplotlib.pyplot as plt
        from matplotlib.patches import Circle
        lines = eval(outputs)['Line']['line']

        line_type = eval(outputs)['Line']['line_type']

        endpoints = eval(outputs)['Line']['line_endpoint']

        fig, ax = plt.subplots(figsize=(3,3), dpi=200)
        ax.set_xlim(-15, 15)
        ax.set_ylim(-15, 15)

        for idx, line in enumerate(lines):
            try:
                p0 = eval(line.split(' -- ')[0])
                p1 = eval(line.split(' -- ')[-1])

                if line_type[idx] == '--':
                    ax.plot([p0[0], p1[0]], [p0[1], p1[1]], linewidth=0.8, color='k')
                else:
                    ax.plot([p0[0], p1[0]], [p0[1], p1[1]], linewidth = 0.8, color = 'k')

                ax.scatter(p0[0], p0[1], s=5, color = 'k')
                ax.scatter(p1[0], p1[1], s=5, color = 'k')
            except:
                pass

        for endpoint in endpoints:
            label = endpoint.split(': ')[0]
            (x, y) = eval(endpoint.split(': ')[1])
            ax.annotate(label, (x, y), xytext=(1, 1), textcoords='offset points', 
                        fontsize=5, fontweight='light')

        try:
            if 'Circle' in eval(outputs).keys():
                circle_centers = eval(outputs)['Circle']['circle_center']
                radius = eval(outputs)['Circle']['radius']

                for center, r in zip(circle_centers, radius):
                    center = eval(center.split(': ')[1])
                    circle = Circle(center, radius=r, fill=False, edgecolor='black', linewidth=0.8)
                    ax.add_patch(circle)
        except:
            pass

        plt.savefig(f'{OUTPUT_PATH}/geo.jpg')
        plt.close()

    # 保存最后生成的线框图
    result.save(f'{OUTPUT_PATH}/result_with_boxes.jpg')


if __name__ == "__main__":
    os.makedirs(OUTPUT_PATH, exist_ok=True)
    os.makedirs(f'{OUTPUT_PATH}/images', exist_ok=True)
    
    document_to_markdown(INPUT_PATH)
