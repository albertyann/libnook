from sqlalchemy.orm import Session
from app.database.models import Note, NoteResource, AISearchTask, KnowledgeCard, ResourceType, AISearchStatus
import uuid
import logging
import os
import requests
import json

logger = logging.getLogger(__name__)

def create_note(db: Session, title: str, content: str = None) -> Note:
    """
    创建新笔记
    """
    note_id = str(uuid.uuid4())[:8]  # 使用8位UUID作为笔记ID
    note = Note(
        id=note_id,
        title=title,
        content=content
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    logger.info(f"创建新笔记: {note_id} - {title}")
    return note

def update_note(db: Session, note_id: str, title: str = None, content: str = None) -> Note:
    """
    更新笔记
    """
    note = db.query(Note).filter(Note.id == note_id).first()
    if not note:
        logger.warning(f"笔记不存在: {note_id}")
        return None
    
    if title is not None:
        note.title = title
    if content is not None:
        note.content = content
    
    db.commit()
    db.refresh(note)
    logger.info(f"更新笔记: {note_id}")
    return note

def delete_note(db: Session, note_id: str) -> bool:
    """
    删除笔记及其相关资源
    """
    note = db.query(Note).filter(Note.id == note_id).first()
    if not note:
        logger.warning(f"笔记不存在: {note_id}")
        return False
    
    # 删除相关资源
    db.query(NoteResource).filter(NoteResource.note_id == note_id).delete()
    db.query(AISearchTask).filter(AISearchTask.note_id == note_id).delete()
    db.query(KnowledgeCard).filter(KnowledgeCard.note_id == note_id).delete()
    
    # 删除笔记
    db.delete(note)
    db.commit()
    
    logger.info(f"删除笔记及其资源: {note_id}")
    return True

def get_note(db: Session, note_id: str) -> Note:
    """
    获取笔记信息
    """
    return db.query(Note).filter(Note.id == note_id).first()

def get_all_notes(db: Session) -> list[Note]:
    """
    获取所有笔记列表
    """
    return db.query(Note).order_by(Note.updated_at.desc()).all()

def add_resource_to_note(db: Session, note_id: str, resource_type: ResourceType, resource_path: str, 
                        original_filename: str = None, resource_metadata: dict = None) -> NoteResource:
    """
    向笔记添加资源
    """
    note = get_note(db, note_id)
    if not note:
        logger.warning(f"笔记不存在: {note_id}")
        return None
    
    resource = NoteResource(
        note_id=note_id,
        resource_type=resource_type,
        resource_path=resource_path,
        original_filename=original_filename,
        resource_metadata=resource_metadata
    )
    db.add(resource)
    db.commit()
    db.refresh(resource)
    
    logger.info(f"向笔记添加资源: {note_id} - {resource_type.value}: {resource_path}")
    return resource

def remove_resource_from_note(db: Session, resource_id: int) -> bool:
    """
    从笔记中移除资源
    """
    resource = db.query(NoteResource).filter(NoteResource.id == resource_id).first()
    if not resource:
        logger.warning(f"资源不存在: {resource_id}")
        return False
    
    # 如果是本地文件，可以选择删除文件
    if resource.resource_type in [ResourceType.PDF, ResourceType.IMAGE]:
        if os.path.exists(resource.resource_path):
            try:
                os.remove(resource.resource_path)
                logger.info(f"删除本地文件: {resource.resource_path}")
            except Exception as e:
                logger.error(f"删除文件失败: {resource.resource_path} - {str(e)}")
    
    # 删除数据库记录
    db.delete(resource)
    db.commit()
    
    logger.info(f"从笔记中移除资源: {resource_id}")
    return True

def get_note_resources(db: Session, note_id: str) -> list[NoteResource]:
    """
    获取笔记的所有资源
    """
    return db.query(NoteResource).filter(NoteResource.note_id == note_id).all()

def create_ai_search_task(db: Session, note_id: str, search_query: str) -> AISearchTask:
    """
    创建AI搜索任务
    """
    task_id = str(uuid.uuid4())[:8]
    task = AISearchTask(
        id=task_id,
        note_id=note_id,
        search_query=search_query,
        status=AISearchStatus.PENDING
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    
    logger.info(f"创建AI搜索任务: {task_id} - 笔记: {note_id} - 查询: {search_query[:50]}...")
    return task

def update_ai_search_task_status(db: Session, task_id: str, status: AISearchStatus, 
                                 search_results: dict = None, error_message: str = None) -> AISearchTask:
    """
    更新AI搜索任务状态
    """
    task = db.query(AISearchTask).filter(AISearchTask.id == task_id).first()
    if not task:
        logger.warning(f"AI搜索任务不存在: {task_id}")
        return None
    
    task.status = status
    if search_results is not None:
        task.search_results = search_results
    if error_message is not None:
        task.error_message = error_message
    
    db.commit()
    db.refresh(task)
    
    logger.info(f"更新AI搜索任务状态: {task_id} -> {status.value}")
    return task

def get_ai_search_tasks(db: Session, note_id: str) -> list[AISearchTask]:
    """
    获取笔记的所有AI搜索任务
    """
    return db.query(AISearchTask).filter(AISearchTask.note_id == note_id).order_by(AISearchTask.created_at.desc()).all()

def perform_ai_search(db: Session, task_id: str) -> AISearchTask:
    """
    执行AI搜索任务
    
    注意：这里是一个模拟实现，实际项目中应该调用真实的AI搜索API
    """
    task = db.query(AISearchTask).filter(AISearchTask.id == task_id).first()
    if not task:
        logger.warning(f"AI搜索任务不存在: {task_id}")
        return None
    
    # 更新状态为处理中
    task = update_ai_search_task_status(db, task_id, AISearchStatus.PROCESSING)
    
    try:
        # 模拟AI搜索过程
        logger.info(f"执行AI搜索: {task_id} - 查询: {task.search_query}")
        
        # 模拟搜索结果
        search_results = {
            "query": task.search_query,
            "sources": [
                {
                    "title": "示例文章1",
                    "url": "https://example.com/article1",
                    "content": "这是示例文章1的内容..."
                },
                {
                    "title": "示例文章2",
                    "url": "https://example.com/article2",
                    "content": "这是示例文章2的内容..."
                }
            ],
            "summary": "这是搜索结果的摘要..."
        }
        
        # 模拟网络请求延迟
        import time
        time.sleep(2)
        
        # 更新任务状态为完成
        task = update_ai_search_task_status(db, task_id, AISearchStatus.COMPLETED, search_results)
        
        # 将搜索结果作为资源添加到笔记
        search_result_resource = {
            "search_query": task.search_query,
            "search_results": search_results,
            "task_id": task_id
        }
        add_resource_to_note(
            db=db,
            note_id=task.note_id,
            resource_type=ResourceType.URL,  # 使用URL类型存储搜索结果
            resource_path=json.dumps(search_result_resource),
            original_filename="ai_search_results.json",
            resource_metadata={"task_id": task_id, "type": "ai_search_result"}
        )
        
    except Exception as e:
        logger.error(f"AI搜索任务失败: {task_id} - {str(e)}")
        task = update_ai_search_task_status(db, task_id, AISearchStatus.ERROR, error_message=str(e))
    
    return task

def generate_knowledge_card(db: Session, note_id: str) -> KnowledgeCard:
    """
    为笔记生成知识卡片
    
    注意：这里是一个模拟实现，实际项目中应该调用真实的AI API生成知识卡片
    """
    note = db.query(Note).filter(Note.id == note_id).first()
    if not note:
        logger.warning(f"笔记不存在: {note_id}")
        return None
    
    # 获取笔记内容和相关资源
    resources = get_note_resources(db, note_id)
    
    # 模拟生成知识卡片
    logger.info(f"为笔记生成知识卡片: {note_id} - {note.title}")
    
    # 收集素材
    materials = {
        "note_title": note.title,
        "note_content": note.content,
        "resources": []
    }
    
    # 更新generate_knowledge_card函数中的metadata引用
    for resource in resources:
        resource_info = {
            "type": resource.resource_type.value,
            "path": resource.resource_path
        }
        if resource.original_filename:
            resource_info["filename"] = resource.original_filename
        if resource.resource_metadata:
            resource_info["resource_metadata"] = resource.resource_metadata
        materials["resources"].append(resource_info)
    
    # 模拟AI生成知识卡片
    import time
    time.sleep(2)
    
    card_id = str(uuid.uuid4())[:8]
    knowledge_card = KnowledgeCard(
        id=card_id,
        note_id=note_id,
        title=f"知识卡片: {note.title}",
        content=f"这是基于笔记'{note.title}'生成的知识卡片内容。\n\n"\
                f"笔记核心要点：{note.content[:100]}..." if note.content else "暂无核心要点",
        tags=[note.title.split()[0]] if note.title else []
    )
    
    db.add(knowledge_card)
    db.commit()
    db.refresh(knowledge_card)
    
    logger.info(f"知识卡片生成成功: {card_id} - 笔记: {note_id}")
    return knowledge_card

def get_knowledge_cards(db: Session, note_id: str) -> list[KnowledgeCard]:
    """
    获取笔记的所有知识卡片
    """
    return db.query(KnowledgeCard).filter(KnowledgeCard.note_id == note_id).order_by(KnowledgeCard.created_at.desc()).all()