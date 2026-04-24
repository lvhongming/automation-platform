from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.database import get_db
from app.models.user import User, Role
from app.schemas.user import RoleResponse, RoleCreate, RoleUpdate
from app.api.deps import get_current_user

router = APIRouter(prefix="/roles", tags=["角色管理"])


@router.get("", response_model=dict)
async def list_roles(
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取角色列表"""
    query = select(Role)
    count_query = select(func.count(Role.id))

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    query = query.order_by(Role.name).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    roles = result.scalars().all()

    return {"total": total, "items": [RoleResponse.model_validate(r) for r in roles]}


@router.get("/{role_id}", response_model=RoleResponse)
async def get_role(
    role_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取角色详情"""
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()

    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")

    return RoleResponse.model_validate(role)


@router.post("", response_model=RoleResponse)
async def create_role(
    role_data: RoleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建角色"""
    # 检查角色名是否存在
    result = await db.execute(select(Role).where(Role.name == role_data.name))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="角色名已存在")

    role = Role(
        name=role_data.name,
        description=role_data.description,
        permissions=role_data.permissions,
        is_system=False
    )
    db.add(role)
    await db.commit()
    await db.refresh(role)

    return RoleResponse.model_validate(role)


@router.put("/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: str,
    role_data: RoleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新角色"""
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()

    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")

    if role.is_system:
        raise HTTPException(status_code=400, detail="系统内置角色不能修改")

    for key, value in role_data.model_dump(exclude_unset=True).items():
        setattr(role, key, value)

    await db.commit()
    await db.refresh(role)

    return RoleResponse.model_validate(role)


@router.delete("/{role_id}")
async def delete_role(
    role_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除角色"""
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()

    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")

    if role.is_system:
        raise HTTPException(status_code=400, detail="系统内置角色不能删除")

    # 检查是否有用户使用该角色
    result = await db.execute(select(User).where(User.role_id == role_id))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="该角色下有用户，无法删除")

    await db.delete(role)
    await db.commit()

    return {"message": "删除成功"}
