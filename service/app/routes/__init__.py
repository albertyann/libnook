# 路由模块初始化文件
from app.routes.pdf import router as pdf_router
from app.routes.notes import router as notes_router

__all__ = ["pdf_router", "notes_router"]