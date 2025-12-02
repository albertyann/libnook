from app.database.database import engine, Base
from app.database.models import PDFDocument, PDFPage
import logging

logger = logging.getLogger(__name__)

def init_database():
    """
    初始化数据库，创建所有表
    """
    try:
        # 创建所有表
        Base.metadata.create_all(bind=engine)
        logger.info("数据库表创建成功")
    except Exception as e:
        logger.error(f"数据库初始化失败: {str(e)}")
        raise