from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Depends
from fastapi.responses import FileResponse
import os
from dotenv import load_dotenv
import uuid
import logging
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.services.note_service import (
    create_note, update_note, delete_note, get_note, get_all_notes,
    add_resource_to_note, remove_resource_from_note, get_note_resources,
    create_ai_search_task, get_ai_search_tasks, perform_ai_search,
    generate_knowledge_card, get_knowledge_cards
)
from app.database.models import ResourceType, AISearchStatus
from pydantic import BaseModel

# 加载环境变量
load_dotenv()

router = APIRouter()
logger = logging.getLogger(__name__)

# 设置上传目录
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")
NOTES_IMAGES_DIR = os.getenv("NOTES_IMAGES_DIR", "./notes_images")

# 确保上传目录存在
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(NOTES_IMAGES_DIR, exist_ok=True)

# 定义请求模型
class NoteCreate(BaseModel):
    title: str
    content: str = None

class NoteUpdate(BaseModel):
    title: str = None
    content: str = None

class AISearchRequest(BaseModel):
    search_query: str

class ResourceURLRequest(BaseModel):
    url: str
    title: str = None

# 创建笔记
@router.post("/notes")
async def create_new_note(note: NoteCreate, db: Session = Depends(get_db)):
    """
    创建新笔记
    """
    try:
        new_note = create_note(
            db=db,
            title=note.title,
            content=note.content
        )
        
        return {
            "note_id": new_note.id,
            "title": new_note.title,
            "content": new_note.content,
            "created_at": new_note.created_at,
            "updated_at": new_note.updated_at,
            "message": "笔记创建成功"
        }
    except Exception as e:
        logger.error(f"创建笔记失败: {str(e)}")
        raise HTTPException(status_code=500, detail="创建笔记失败")

# 获取笔记列表
@router.get("/notes")
async def get_notes_list(db: Session = Depends(get_db)):
    """
    获取所有笔记列表
    """
    try:
        notes = get_all_notes(db)
        return [
            {
                "note_id": note.id,
                "title": note.title,
                "content": note.content,
                "created_at": note.created_at,
                "updated_at": note.updated_at
            }
            for note in notes
        ]
    except Exception as e:
        logger.error(f"获取笔记列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取笔记列表失败")

# 获取笔记详情
@router.get("/notes/{note_id}")
async def get_note_details(note_id: str, db: Session = Depends(get_db)):
    """
    获取笔记详情
    """
    try:
        note = get_note(db, note_id)
        if not note:
            raise HTTPException(status_code=404, detail="笔记不存在")
        
        # 获取笔记资源
        resources = get_note_resources(db, note_id)
        
        return {
            "note_id": note.id,
            "title": note.title,
            "content": note.content,
            "created_at": note.created_at,
            "updated_at": note.updated_at,
            "resources": [
                {
                    "resource_id": resource.id,
                    "type": resource.resource_type.value,
                    "path": resource.resource_path,
                    "original_filename": resource.original_filename,
                    "resource_metadata": resource.resource_metadata,
                    "created_at": resource.created_at
                }
                for resource in resources
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取笔记详情失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取笔记详情失败")

# 更新笔记
@router.put("/notes/{note_id}")
async def update_note_details(note_id: str, note: NoteUpdate, db: Session = Depends(get_db)):
    """
    更新笔记内容
    """
    try:
        updated_note = update_note(
            db=db,
            note_id=note_id,
            title=note.title,
            content=note.content
        )
        
        if not updated_note:
            raise HTTPException(status_code=404, detail="笔记不存在")
        
        return {
            "note_id": updated_note.id,
            "title": updated_note.title,
            "content": updated_note.content,
            "created_at": updated_note.created_at,
            "updated_at": updated_note.updated_at,
            "message": "笔记更新成功"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新笔记失败: {str(e)}")
        raise HTTPException(status_code=500, detail="更新笔记失败")

# 删除笔记
@router.delete("/notes/{note_id}")
async def delete_note_by_id(note_id: str, db: Session = Depends(get_db)):
    """
    删除笔记
    """
    try:
        success = delete_note(db, note_id)
        if not success:
            raise HTTPException(status_code=404, detail="笔记不存在")
        
        return {
            "message": "笔记删除成功"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除笔记失败: {str(e)}")
        raise HTTPException(status_code=500, detail="删除笔记失败")

# 向笔记添加PDF资源
@router.post("/notes/{note_id}/resources/pdf")
async def add_pdf_resource(
    note_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    向笔记添加PDF资源
    """
    try:
        # 检查文件类型
        if not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="只支持PDF文件")
        
        # 保存文件
        file_id = str(uuid.uuid4())[:8]
        file_path = os.path.join(UPLOAD_DIR, f"note_{note_id}_{file_id}.pdf")
        
        with open(file_path, "wb") as f:
            f.write(await file.read())
        
        # 添加资源到笔记
        resource = add_resource_to_note(
            db=db,
            note_id=note_id,
            resource_type=ResourceType.PDF,
            resource_path=file_path,
            original_filename=file.filename
        )
        
        if not resource:
            raise HTTPException(status_code=404, detail="笔记不存在")
        
        return {
            "resource_id": resource.id,
            "note_id": resource.note_id,
            "type": resource.resource_type.value,
            "path": resource.resource_path,
            "original_filename": resource.original_filename,
            "created_at": resource.created_at,
            "message": "PDF资源添加成功"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"添加PDF资源失败: {str(e)}")
        raise HTTPException(status_code=500, detail="添加PDF资源失败")

# 向笔记添加图片资源
@router.post("/notes/{note_id}/resources/image")
async def add_image_resource(
    note_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    向笔记添加图片资源
    """
    try:
        # 检查文件类型
        allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.svg']
        file_extension = os.path.splitext(file.filename)[1].lower()
        if file_extension not in allowed_extensions:
            raise HTTPException(status_code=400, detail="只支持图片文件 (jpg, jpeg, png, gif, svg)")
        
        # 保存文件
        file_id = str(uuid.uuid4())[:8]
        file_path = os.path.join(NOTES_IMAGES_DIR, f"note_{note_id}_{file_id}{file_extension}")
        
        with open(file_path, "wb") as f:
            f.write(await file.read())
        
        # 添加资源到笔记
        resource = add_resource_to_note(
            db=db,
            note_id=note_id,
            resource_type=ResourceType.IMAGE,
            resource_path=file_path,
            original_filename=file.filename
        )
        
        if not resource:
            raise HTTPException(status_code=404, detail="笔记不存在")
        
        return {
            "resource_id": resource.id,
            "note_id": resource.note_id,
            "type": resource.resource_type.value,
            "path": resource.resource_path,
            "original_filename": resource.original_filename,
            "created_at": resource.created_at,
            "message": "图片资源添加成功"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"添加图片资源失败: {str(e)}")
        raise HTTPException(status_code=500, detail="添加图片资源失败")

# 向笔记添加URL资源
@router.post("/notes/{note_id}/resources/url")
async def add_url_resource(
    note_id: str,
    url_request: ResourceURLRequest,
    db: Session = Depends(get_db)
):
    """
    向笔记添加URL资源
    """
    try:
        # 添加URL资源到笔记
        resource = add_resource_to_note(
            db=db,
            note_id=note_id,
            resource_type=ResourceType.URL,
            resource_path=url_request.url,
            resource_metadata={"title": url_request.title} if url_request.title else None
        )
        
        if not resource:
            raise HTTPException(status_code=404, detail="笔记不存在")
        
        return {
            "resource_id": resource.id,
            "note_id": resource.note_id,
            "type": resource.resource_type.value,
            "url": resource.resource_path,
            "title": resource.resource_metadata.get("title") if resource.resource_metadata else None,
            "created_at": resource.created_at,
            "message": "URL资源添加成功"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"添加URL资源失败: {str(e)}")
        raise HTTPException(status_code=500, detail="添加URL资源失败")

# 删除笔记资源
@router.delete("/notes/resources/{resource_id}")
async def remove_resource(resource_id: int, db: Session = Depends(get_db)):
    """
    删除笔记资源
    """
    try:
        success = remove_resource_from_note(db, resource_id)
        if not success:
            raise HTTPException(status_code=404, detail="资源不存在")
        
        return {
            "message": "资源删除成功"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除资源失败: {str(e)}")
        raise HTTPException(status_code=500, detail="删除资源失败")

# 获取笔记资源列表
@router.get("/notes/{note_id}/resources")
async def get_resources(note_id: str, db: Session = Depends(get_db)):
    """
    获取笔记的所有资源
    """
    try:
        resources = get_note_resources(db, note_id)
        return [
            {
                "resource_id": resource.id,
                "type": resource.resource_type.value,
                "path": resource.resource_path,
                "original_filename": resource.original_filename,
                "resource_metadata": resource.resource_metadata,
                "created_at": resource.created_at
            }
            for resource in resources
        ]
    except Exception as e:
        logger.error(f"获取资源列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取资源列表失败")

# 创建AI搜索任务
@router.post("/notes/{note_id}/ai-search")
async def create_search_task(
    note_id: str,
    search_request: AISearchRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    创建AI搜索任务
    """
    try:
        # 检查笔记是否存在
        if not get_note(db, note_id):
            raise HTTPException(status_code=404, detail="笔记不存在")
        
        # 创建搜索任务
        task = create_ai_search_task(db, note_id, search_request.search_query)
        
        # 添加后台任务执行搜索
        background_tasks.add_task(perform_ai_search_background, task.id)
        
        return {
            "task_id": task.id,
            "note_id": task.note_id,
            "search_query": task.search_query,
            "status": task.status.value,
            "created_at": task.created_at,
            "message": "AI搜索任务创建成功，正在执行搜索"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建AI搜索任务失败: {str(e)}")
        raise HTTPException(status_code=500, detail="创建AI搜索任务失败")

# 获取笔记的AI搜索任务列表
@router.get("/notes/{note_id}/ai-search")
async def get_search_tasks(note_id: str, db: Session = Depends(get_db)):
    """
    获取笔记的所有AI搜索任务
    """
    try:
        tasks = get_ai_search_tasks(db, note_id)
        return [
            {
                "task_id": task.id,
                "note_id": task.note_id,
                "search_query": task.search_query,
                "status": task.status.value,
                "search_results": task.search_results,
                "error_message": task.error_message,
                "created_at": task.created_at,
                "updated_at": task.updated_at
            }
            for task in tasks
        ]
    except Exception as e:
        logger.error(f"获取搜索任务列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取搜索任务列表失败")

# 生成知识卡片
@router.post("/notes/{note_id}/knowledge-cards")
async def generate_card(
    note_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    生成知识卡片
    """
    try:
        # 检查笔记是否存在
        if not get_note(db, note_id):
            raise HTTPException(status_code=404, detail="笔记不存在")
        
        # 生成知识卡片
        card = generate_knowledge_card(db, note_id)
        
        if not card:
            raise HTTPException(status_code=500, detail="生成知识卡片失败")
        
        return {
            "card_id": card.id,
            "note_id": card.note_id,
            "title": card.title,
            "content": card.content,
            "created_at": card.created_at,
            "message": "知识卡片生成成功"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成知识卡片失败: {str(e)}")
        raise HTTPException(status_code=500, detail="生成知识卡片失败")

# 获取知识卡片列表
@router.get("/notes/{note_id}/knowledge-cards")
async def get_cards(note_id: str, db: Session = Depends(get_db)):
    """
    获取笔记的所有知识卡片
    """
    try:
        cards = get_knowledge_cards(db, note_id)
        return [
            {
                "card_id": card.id,
                "note_id": card.note_id,
                "title": card.title,
                "content": card.content,
                "created_at": card.created_at
            }
            for card in cards
        ]
    except Exception as e:
        logger.error(f"获取知识卡片列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取知识卡片列表失败")

# 后台任务函数
def perform_ai_search_background(task_id: str):
    """
    执行AI搜索任务的后台函数
    """
    from app.database.database import SessionLocal
    
    db = SessionLocal()
    try:
        perform_ai_search(db, task_id)
    except Exception as e:
        logger.error(f"后台执行AI搜索任务失败: {str(e)}")
    finally:
        db.close()

def generate_knowledge_card_background(note_id: str):
    """
    生成知识卡片的后台函数
    """
    from app.database.database import SessionLocal
    
    db = SessionLocal()
    try:
        generate_knowledge_card(db, note_id)
    except Exception as e:
        logger.error(f"后台生成知识卡片失败: {str(e)}")
    finally:
        db.close()