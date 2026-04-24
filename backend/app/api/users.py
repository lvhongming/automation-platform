from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional

from app.db.database import get_db
from app.models.user import User
from app.models.user import Role
from app.schemas.user import UserResponse, UserCreate, UserUpdate
from app.schemas.user import RoleResponse, RoleCreate, RoleUpdate
from app.api.deps import get_current_user
from app.core.security import get_password_hash

router = APIRouter(prefix="/users", tags=["用户管理"])


@router.get("", response_model=dict)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取用户列表"""
    query = select(User)
    count_query = select(func.count(User.id))

    if keyword:
        search = f"%{keyword}%"
        query = query.where(
            (User.username.ilike(search)) |
            (User.email.ilike(search)) |
            (User.full_name.ilike(search))
        )
        count_query = count_query.where(
            (User.username.ilike(search)) |
            (User.email.ilike(search)) |
            (User.full_name.ilike(search))
        )

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    query = query.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    users = result.scalars().all()

    items = []
    for user in users:
        item = UserResponse.model_validate(user).model_dump()
        if user.role_id:
            role_result = await db.execute(select(Role).where(Role.id == user.role_id))
            role = role_result.scalar_one_or_none()
            item["role_name"] = role.name if role else None
        items.append(item)

    return {"total": total, "items": items}


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取用户详情"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    return UserResponse.model_validate(user)


@router.post("", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建用户"""
    # 检查用户名是否存在
    result = await db.execute(select(User).where(User.username == user_data.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="用户名已存在")

    # 检查邮箱是否存在
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="邮箱已被使用")

    # 创建用户
    user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        phone=user_data.phone,
        department=user_data.department,
        role_id=user_data.role_id,
        is_active=True
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return UserResponse.model_validate(user)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新用户"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 检查邮箱是否被其他用户使用
    if user_data.email:
        result = await db.execute(
            select(User).where(
                User.email == user_data.email,
                User.id != user_id
            )
        )
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="邮箱已被其他用户使用")

    update_data = user_data.model_dump(exclude_unset=True)

    # 如果有密码，更新密码
    if 'password' in update_data and update_data['password']:
        user.password_hash = get_password_hash(update_data['password'])
        del update_data['password']

    for key, value in update_data.items():
        setattr(user, key, value)

    await db.commit()
    await db.refresh(user)

    return UserResponse.model_validate(user)


@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除用户"""
    # 不能删除自己
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="不能删除当前登录用户")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    await db.delete(user)
    await db.commit()

    return {"message": "删除成功"}


@router.post("/{user_id}/toggle-status")
async def toggle_user_status(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """切换用户状态"""
    # 不能禁用自己
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="不能禁用当前登录用户")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    user.is_active = not user.is_active
    await db.commit()

    return {"message": "操作成功", "is_active": user.is_active}
