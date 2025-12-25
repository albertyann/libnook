# PDF OCR API

一个基于FastAPI的PDF文件处理和OCR识别服务。

## 功能特点

- PDF文件上传
- 自动解析PDF文件信息
- SQLite数据库存储
- PDF文件按页切割并转换为图片
- 远程API调用进行OCR文字识别
- RESTful API接口

## 技术栈

- Python 3.8+
- FastAPI
- SQLite + SQLAlchemy
- PyPDF2 (PDF解析)
- pdf2image (PDF转图片)
- Pillow (图像处理)
- requests (HTTP请求)

## 安装和运行

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 文件并修改为 `.env`，然后根据需要修改配置：

```bash
cp .env.example .env
```

主要配置项：
- `OCR_API_URL`: 远程OCR API地址
- `OCR_API_KEY`: 远程OCR API密钥
- `MAX_FILE_SIZE`: 最大文件大小限制
- `UPLOAD_DIR`: 上传文件目录
- `IMAGES_DIR`: 生成图片目录
- `DATABASE_URL`: 数据库连接URL

### 3. 运行服务

```bash
python main.py
```

或者使用uvicorn直接运行：

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. 访问API文档

服务启动后，可以访问以下地址查看API文档：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API接口

### 1. 上传PDF文件

```
POST /api/pdf/upload
```

请求体：multipart/form-data，包含file字段

响应：
```json
{
  "file_id": "uuid-string",
  "original_filename": "example.pdf",
  "status": "uploaded",
  "message": "文件上传成功，等待处理"
}
```

### 2. 查询文件处理状态

```
GET /api/pdf/status/{file_id}
```

响应：
```json
{
  "file_id": "uuid-string",
  "original_filename": "example.pdf",
  "status": "ocr_completed",
  "total_pages": 10,
  "pages_processed": 10,
  "error_message": null,
  "created_at": "2024-01-01T12:00:00Z"
}
```

### 3. 获取OCR识别结果

```
GET /api/pdf/ocr/{file_id}
GET /api/pdf/ocr/{file_id}?page=1  # 获取指定页的结果
```

响应：
```json
{
  "file_id": "uuid-string",
  "original_filename": "example.pdf",
  "total_pages": 10,
  "pages_with_ocr": 10,
  "results": [
    {
      "page": 1,
      "text": "识别出的文本内容...",
      "processed_at": "2024-01-01T12:01:00Z"
    },
    // 更多页...
  ]
}
```

## 处理流程

1. 上传PDF文件
2. 解析PDF文件信息并保存到数据库
3. 将PDF按页切割并转换为图片
4. 对每张图片调用远程OCR API进行文字识别
5. 保存识别结果到数据库

## 注意事项

- 确保安装了pdf2image所需的系统依赖：poppler
- 远程OCR API需要正确配置URL和密钥
- 对于大文件处理，可能需要调整超时设置

## 开发说明

- 使用了模块化架构，便于扩展和维护
- 实现了完整的错误处理和日志记录
- 支持后台异步处理，不阻塞API响应