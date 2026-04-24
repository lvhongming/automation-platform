from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone, timedelta

from app.db.database import get_db
from app.core.utils import now
from app.core.security import (
    verify_password, get_password_hash,
    create_access_token
)
from app.models.user import User, Role
from app.schemas.user import (
    LoginRequest, LoginResponse, UserResponse,
    UserCreate, UserUpdate, RoleCreate, RoleResponse
)
from app.api.deps import get_current_user
from app.core.utils import now

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/login", response_model=LoginResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """用户登录"""
    result = await db.execute(
        select(User).where(User.username == form_data.username)
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户已被禁用"
        )

    # 获取用户角色和权限
    role = None
    permissions = []
    if user.role_id:
        role_result = await db.execute(
            select(Role).where(Role.id == user.role_id)
        )
        role = role_result.scalar_one_or_none()
        if role:
            permissions = role.permissions or []

    # 创建访问令牌
    access_token = create_access_token(
        subject=str(user.id),
        extra_claims={
            "username": user.username,
            "role": role.name if role else "user"
        }
    )

    # 更新最后登录时间
    user.last_login_at = now()
    await db.commit()

    return LoginResponse(
        token=access_token,
        user=UserResponse.model_validate(user),
        permissions=[{"resource": p.split(":")[0], "actions": [p.split(":")[1]]} for p in permissions]
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取当前用户信息"""
    # 获取角色信息
    role = None
    if current_user.role_id:
        result = await db.execute(
            select(Role).where(Role.id == current_user.role_id)
        )
        role = result.scalar_one_or_none()

    user_data = UserResponse.model_validate(current_user)
    if role:
        user_data.role_id = current_user.role_id

    return user_data


@router.post("/register", response_model=UserResponse)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """用户注册"""
    # 检查用户名是否存在
    result = await db.execute(
        select(User).where(User.username == user_data.username)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在"
        )

    # 检查邮箱是否存在
    result = await db.execute(
        select(User).where(User.email == user_data.email)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱已被使用"
        )

    # 获取默认角色
    result = await db.execute(select(Role).where(Role.name == "user"))
    default_role = result.scalar_one_or_none()

    # 创建用户
    user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        phone=user_data.phone,
        department=user_data.department,
        role_id=default_role.id if default_role else None
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return UserResponse.model_validate(user)


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    """用户登出（前端删除令牌即可）"""
    return {"message": "登出成功"}


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新当前用户信息"""
    # 检查邮箱是否被其他用户使用
    if user_data.email:
        result = await db.execute(
            select(User).where(
                User.email == user_data.email,
                User.id != current_user.id
            )
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="邮箱已被其他用户使用"
            )

    # 更新用户信息
    update_data = user_data.model_dump(exclude_unset=True)

    # 如果有密码，更新密码哈希
    if 'password' in update_data and update_data['password']:
        current_user.password_hash = get_password_hash(update_data['password'])
        del update_data['password']

    for key, value in update_data.items():
        setattr(current_user, key, value)

    await db.commit()
    await db.refresh(current_user)

    return UserResponse.model_validate(current_user)
