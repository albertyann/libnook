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


from openai import OpenAI

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

client = OpenAI(
    api_key="EMPTY",
    base_url="http://localhost:8000/v1",
    timeout=3600
)

image_path=INPUT_PATH
with open(image_path, "rb") as f:
    image_bytes = f.read()

image = load_image(image_path).convert('RGB')

base64_image = base64.b64encode(image_bytes).decode('utf-8')

messages = [
    {"role": "system", "content": ""},
    {
        "role": "user",
        "content": [
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{base64_image}"
                }
            },
            {
                "type": "text",
                "text": PROMPT
            }
        ]
    }
]

response = client.chat.completions.create(
    model="tencent/HunyuanOCR",
    messages=messages,
    temperature=0.0,
    extra_body={
        "top_k": 1,
        "repetition_penalty": 1.0
    },
)
print(f"Generated text: {response.choices[0].message.content}")
