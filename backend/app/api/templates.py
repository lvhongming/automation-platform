from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional, List

from app.db.database import get_db
from app.models.flow import PlaybookTemplate, ScriptTemplate
from app.models.user import User
from app.schemas.flow import (
    PlaybookTemplateCreate, PlaybookTemplateUpdate, PlaybookTemplateResponse,
    ScriptTemplateCreate, ScriptTemplateUpdate, ScriptTemplateResponse
)
from app.api.deps import get_current_user

router = APIRouter(prefix="/templates", tags=["模板管理"])


# ============ Playbook 模板 ============

@router.get("/playbooks", response_model=dict)
async def list_playbooks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: Optional[str] = None,
    keyword: Optional[str] = None,
    tags: Optional[str] = None,  # 标签搜索，逗号分隔
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取 Playbook 模板列表"""
    query = select(PlaybookTemplate)
    count_query = select(func.count(PlaybookTemplate.id))

    if category:
        query = query.where(PlaybookTemplate.category == category)
        count_query = count_query.where(PlaybookTemplate.category == category)

    if keyword:
        query = query.where(
            PlaybookTemplate.name.contains(keyword) |
            PlaybookTemplate.description.contains(keyword)
        )
        count_query = count_query.where(
            PlaybookTemplate.name.contains(keyword) |
            PlaybookTemplate.description.contains(keyword)
        )

    if tags:
        tag_list = [t.strip() for t in tags.split(',') if t.strip()]
        for tag in tag_list:
            query = query.where(PlaybookTemplate.tags.contains(tag))
            count_query = count_query.where(PlaybookTemplate.tags.contains(tag))

    # 只获取公开模板或用户创建的模板
    query = query.where(
        (PlaybookTemplate.is_public == True) |
        (PlaybookTemplate.created_by == current_user.id)
    )

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    query = query.order_by(PlaybookTemplate.updated_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()

    return {"total": total, "items": [PlaybookTemplateResponse.model_validate(i) for i in items]}


@router.get("/playbooks/{playbook_id}", response_model=PlaybookTemplateResponse)
async def get_playbook(
    playbook_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取 Playbook 详情"""
    result = await db.execute(select(PlaybookTemplate).where(PlaybookTemplate.id == playbook_id))
    playbook = result.scalar_one_or_none()

    if not playbook:
        raise HTTPException(status_code=404, detail="模板不存在")

    return PlaybookTemplateResponse.model_validate(playbook)


@router.post("/playbooks", response_model=PlaybookTemplateResponse)
async def create_playbook(
    playbook_data: PlaybookTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建 Playbook 模板"""
    playbook = PlaybookTemplate(
        **playbook_data.model_dump(),
        created_by=current_user.id
    )
    db.add(playbook)
    await db.commit()
    await db.refresh(playbook)
    return PlaybookTemplateResponse.model_validate(playbook)


@router.put("/playbooks/{playbook_id}", response_model=PlaybookTemplateResponse)
async def update_playbook(
    playbook_id: str,
    playbook_data: PlaybookTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新 Playbook 模板"""
    result = await db.execute(select(PlaybookTemplate).where(PlaybookTemplate.id == playbook_id))
    playbook = result.scalar_one_or_none()

    if not playbook:
        raise HTTPException(status_code=404, detail="模板不存在")

    for key, value in playbook_data.model_dump(exclude_unset=True).items():
        setattr(playbook, key, value)

    await db.commit()
    await db.refresh(playbook)
    return PlaybookTemplateResponse.model_validate(playbook)


@router.delete("/playbooks/{playbook_id}")
async def delete_playbook(
    playbook_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除 Playbook 模板"""
    result = await db.execute(select(PlaybookTemplate).where(PlaybookTemplate.id == playbook_id))
    playbook = result.scalar_one_or_none()

    if not playbook:
        raise HTTPException(status_code=404, detail="模板不存在")

    # 检查权限
    if playbook.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="无权限删除")

    await db.delete(playbook)
    await db.commit()
    return {"message": "删除成功"}


@router.post("/playbooks/{playbook_id}/copy", response_model=PlaybookTemplateResponse)
async def copy_playbook(
    playbook_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """复制 Playbook 模板"""
    result = await db.execute(select(PlaybookTemplate).where(PlaybookTemplate.id == playbook_id))
    playbook = result.scalar_one_or_none()

    if not playbook:
        raise HTTPException(status_code=404, detail="模板不存在")

    # 创建副本
    new_playbook = PlaybookTemplate(
        name=f"{playbook.name} (副本)",
        description=playbook.description,
        category=playbook.category,
        tags=playbook.tags,
        content=playbook.content,
        is_public=False,  # 副本默认为非公开
        created_by=current_user.id
    )
    db.add(new_playbook)
    await db.commit()
    await db.refresh(new_playbook)
    return PlaybookTemplateResponse.model_validate(new_playbook)


# ============ 脚本模板 ============

@router.get("/scripts", response_model=dict)
async def list_scripts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    script_type: Optional[str] = None,
    keyword: Optional[str] = None,
    tags: Optional[str] = None,  # 标签搜索，逗号分隔
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取脚本模板列表"""
    query = select(ScriptTemplate)
    count_query = select(func.count(ScriptTemplate.id))

    if script_type:
        query = query.where(ScriptTemplate.script_type == script_type)
        count_query = count_query.where(ScriptTemplate.script_type == script_type)

    if keyword:
        query = query.where(
            ScriptTemplate.name.contains(keyword) |
            ScriptTemplate.description.contains(keyword)
        )
        count_query = count_query.where(
            ScriptTemplate.name.contains(keyword) |
            ScriptTemplate.description.contains(keyword)
        )

    if tags:
        tag_list = [t.strip() for t in tags.split(',') if t.strip()]
        for tag in tag_list:
            query = query.where(ScriptTemplate.tags.contains(tag))
            count_query = count_query.where(ScriptTemplate.tags.contains(tag))

    query = query.where(
        (ScriptTemplate.is_public == True) |
        (ScriptTemplate.created_by == current_user.id)
    )

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    query = query.order_by(ScriptTemplate.updated_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()

    return {"total": total, "items": [ScriptTemplateResponse.model_validate(i) for i in items]}


@router.get("/scripts/{script_id}", response_model=ScriptTemplateResponse)
async def get_script(
    script_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取脚本详情"""
    result = await db.execute(select(ScriptTemplate).where(ScriptTemplate.id == script_id))
    script = result.scalar_one_or_none()

    if not script:
        raise HTTPException(status_code=404, detail="模板不存在")

    return ScriptTemplateResponse.model_validate(script)


@router.post("/scripts", response_model=ScriptTemplateResponse)
async def create_script(
    script_data: ScriptTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建脚本模板"""
    script = ScriptTemplate(
        **script_data.model_dump(),
        created_by=current_user.id
    )
    db.add(script)
    await db.commit()
    await db.refresh(script)
    return ScriptTemplateResponse.model_validate(script)


@router.put("/scripts/{script_id}", response_model=ScriptTemplateResponse)
async def update_script(
    script_id: str,
    script_data: ScriptTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新脚本模板"""
    result = await db.execute(select(ScriptTemplate).where(ScriptTemplate.id == script_id))
    script = result.scalar_one_or_none()

    if not script:
        raise HTTPException(status_code=404, detail="模板不存在")

    for key, value in script_data.model_dump(exclude_unset=True).items():
        setattr(script, key, value)

    await db.commit()
    await db.refresh(script)
    return ScriptTemplateResponse.model_validate(script)


@router.delete("/scripts/{script_id}")
async def delete_script(
    script_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除脚本模板"""
    result = await db.execute(select(ScriptTemplate).where(ScriptTemplate.id == script_id))
    script = result.scalar_one_or_none()

    if not script:
        raise HTTPException(status_code=404, detail="模板不存在")

    if script.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="无权限删除")

    await db.delete(script)
    await db.commit()
    return {"message": "删除成功"}


@router.post("/scripts/{script_id}/copy", response_model=ScriptTemplateResponse)
async def copy_script(
    script_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """复制脚本模板"""
    result = await db.execute(select(ScriptTemplate).where(ScriptTemplate.id == script_id))
    script = result.scalar_one_or_none()

    if not script:
        raise HTTPException(status_code=404, detail="模板不存在")

    # 创建副本
    new_script = ScriptTemplate(
        name=f"{script.name} (副本)",
        description=script.description,
        script_type=script.script_type,
        tags=script.tags,
        content=script.content,
        is_public=False,  # 副本默认为非公开
        created_by=current_user.id
    )
    db.add(new_script)
    await db.commit()
    await db.refresh(new_script)
    return ScriptTemplateResponse.model_validate(new_script)
