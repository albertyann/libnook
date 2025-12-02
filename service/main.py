from fastapi import FastAPI, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
import logging
from app.database.db_init import init_database

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建必要的目录
os.makedirs(os.getenv("UPLOAD_DIR", "./uploads"), exist_ok=True)
os.makedirs(os.getenv("IMAGES_DIR", "./images"), exist_ok=True)

# 创建FastAPI应用
app = FastAPI(
    title="PDF OCR API",
    description="一个用于PDF文件上传、解析、切割和OCR识别的API服务",
    version="1.0.0"
)

# 应用启动事件
@app.on_event("startup")
async def startup_event():
    logger.info("应用启动，初始化数据库...")
    init_database()
    logger.info("应用启动完成")

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该设置具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "PDF OCR API服务运行中"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# 导入路由
from app.routes import pdf
app.include_router(pdf.router, prefix="/api/pdf", tags=["pdf"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)