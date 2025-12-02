#!/bin/bash

# 检查是否安装了虚拟环境
if [ ! -d "venv" ]; then
    echo "创建虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
echo "激活虚拟环境..."
source venv/bin/activate

# 安装依赖
echo "安装依赖..."
pip install -r requirements.txt

# 检查是否存在.env文件
if [ ! -f ".env" ]; then
    echo "创建.env文件..."
    cp .env.example .env
    echo "请编辑.env文件配置OCR API信息"
fi

# 创建必要的目录
mkdir -p uploads
mkdir -p images

# 启动服务
echo "启动服务..."
python main.py