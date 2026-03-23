"""
认证接口
POST /api/v1/auth/login - 账号密码登录
POST /api/v1/auth/sms-login - 手机验证码登录
POST /api/v1/auth/register - 用户注册
"""
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.database import get_db, User
from app.config import settings

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

# ========================
# Pydantic 模型
# ========================

class LoginRequest(BaseModel):
    """账号密码登录请求"""
    username: str  # 支持 username 或 email
    password: str
    remember_me: bool = False  # 7天免登录


class SmsLoginRequest(BaseModel):
    """手机验证码登录请求"""
    phone: str
    code: str  # 验证码


class RegisterRequest(BaseModel):
    """用户注册请求"""
    username: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    password: str

    @field_validator("username")
    @classmethod
    def username_length(cls, v: str) -> str:
        if len(v) < 3:
            raise ValueError("用户名长度至少3位")
        if len(v) > 50:
            raise ValueError("用户名长度最多50位")
        if not re.match(r"^[a-zA-Z0-9_]+$", v):
            raise ValueError("用户名只能包含字母、数字和下划线")
        return v

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("密码长度至少8位")
        return v

    @field_validator("phone")
    @classmethod
    def phone_format(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not re.match(r"^1[3-9]\d{9}$", v):
            raise ValueError("手机号格式不正确")
        return v


class AuthResponse(BaseModel):
    """认证响应"""
    user_id: str
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class SendCodeRequest(BaseModel):
    """发送验证码请求"""
    phone: str

    @field_validator("phone")
    @classmethod
    def phone_format(cls, v: str) -> str:
        if not re.match(r"^1[3-9]\d{9}$", v):
            raise ValueError("手机号格式不正确")
        return v


class SendCodeResponse(BaseModel):
    """发送验证码响应"""
    message: str
    # 演示模式下返回验证码供测试
    code: Optional[str] = None


# ========================
# 验证码存储（生产环境用 Redis）
# ========================

# 演示用：内存存储验证码（TODO: 生产环境用 Redis）
_sms_codes: dict[str, tuple[str, float]] = {}  # {phone: (code, expire_timestamp)}


# ========================
# 登录安全：登录尝试追踪
# ========================

# {username_or_ip: (failed_count, last_attempt_timestamp, is_locked)}
_login_attempts: dict[str, tuple[int, float, bool]] = {}
MAX_LOGIN_ATTEMPTS = 5  # 最多失败次数
LOGIN_LOCKOUT_SECONDS = 300  # 锁定 5 分钟


# ========================
# 业务逻辑函数
# ========================

def hash_password(password: str) -> str:
    """使用 bcrypt 对密码进行哈希"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """校验密码"""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8")
    )


def create_tokens(user_id: str, remember_me: bool = False) -> tuple[str, str, int]:
    """
    创建 access_token 和 refresh_token
    remember_me=True 时 access_token 有效期为 7 天，否则 24 小时
    """
    if remember_me:
        expire_minutes = settings.refresh_token_expire_days * 24 * 60
    else:
        expire_minutes = settings.access_token_expire_minutes

    expire = datetime.now(timezone.utc) + timedelta(minutes=expire_minutes)

    # Access token
    access_payload = {
        "sub": user_id,
        "type": "access",
        "exp": expire,
        "iat": datetime.now(timezone.utc)
    }
    access_token = jwt.encode(
        access_payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm
    )

    # Refresh token (always 7 days)
    refresh_expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    refresh_payload = {
        "sub": user_id,
        "type": "refresh",
        "exp": refresh_expire,
        "iat": datetime.now(timezone.utc)
    }
    refresh_token = jwt.encode(
        refresh_payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm
    )

    return access_token, refresh_token, expire_minutes * 60


def _check_login_attempt(identifier: str) -> None:
    """检查登录是否被锁定"""
    now = time.time()
    if identifier in _login_attempts:
        count, last_attempt, is_locked = _login_attempts[identifier]
        if is_locked and now - last_attempt < LOGIN_LOCKOUT_SECONDS:
            remaining = int(LOGIN_LOCKOUT_SECONDS - (now - last_attempt))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"登录尝试过多，请 {remaining} 秒后重试"
            )
        # 重置过期的记录
        if now - last_attempt >= LOGIN_LOCKOUT_SECONDS:
            del _login_attempts[identifier]


def _record_failed_attempt(identifier: str) -> None:
    """记录失败的登录尝试"""
    now = time.time()
    if identifier in _login_attempts:
        count, last_attempt, _ = _login_attempts[identifier]
        new_count = count + 1
    else:
        new_count = 1

    is_locked = new_count >= MAX_LOGIN_ATTEMPTS
    _login_attempts[identifier] = (new_count, now, is_locked)


def _clear_login_attempt(identifier: str) -> None:
    """清除登录尝试记录"""
    _login_attempts.pop(identifier, None)


def decode_token(token: str) -> dict:
    """解码 JWT token"""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 已过期"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的 Token"
        )


def generate_sms_code() -> str:
    """生成6位验证码"""
    import random
    return str(random.randint(100000, 999999))


def _store_sms_code(phone: str, code: str) -> None:
    """存储验证码（5分钟有效期）"""
    import time
    _sms_codes[phone] = (code, time.time() + 300)  # 5分钟有效期


def _verify_sms_code(phone: str, code: str) -> bool:
    """验证验证码（检查有效期）"""
    import time
    if phone not in _sms_codes:
        return False
    stored_code, expire_time = _sms_codes[phone]
    if time.time() > expire_time:
        del _sms_codes[phone]
        return False
    return stored_code == code


# ========================
# API 路由
# ========================

@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(user_in: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """
    用户注册
    支持 username/email/phone 注册
    """
    # 1. 检查用户名是否已存在
    result = await db.execute(select(User).where(User.username == user_in.username))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已被注册"
        )

    # 2. 检查邮箱是否已被使用
    if user_in.email:
        result = await db.execute(select(User).where(User.email == user_in.email))
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="邮箱已被注册"
            )

    # 3. 检查手机号是否已被使用
    if user_in.phone:
        result = await db.execute(select(User).where(User.phone == user_in.phone))
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="手机号已被注册"
            )

    # 4. 创建用户
    hashed_pwd = hash_password(user_in.password)
    new_user = User(
        username=user_in.username,
        email=user_in.email,
        phone=user_in.phone,
        hashed_password=hashed_pwd
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # 5. 生成 token
    access_token, refresh_token, expires_in = create_tokens(new_user.id)

    return AuthResponse(
        user_id=new_user.id,
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in
    )


@router.post("/login", response_model=AuthResponse)
async def login(login_req: LoginRequest, db: AsyncSession = Depends(get_db)):
    """
    账号密码登录
    支持 username 或 email 登录
    支持 remember_me 参数实现 7 天免登录
    """
    # 0. 检查登录锁定状态
    _check_login_attempt(login_req.username)

    # 1. 查找用户
    result = await db.execute(
        select(User).where(
            (User.username == login_req.username) |
            (User.email == login_req.username)
        )
    )
    user = result.scalar_one_or_none()

    if not user:
        _record_failed_attempt(login_req.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )

    # 2. 验证密码
    if not verify_password(login_req.password, user.hashed_password):
        _record_failed_attempt(login_req.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )

    # 3. 检查用户状态
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用"
        )

    # 4. 清除登录尝试记录
    _clear_login_attempt(login_req.username)

    # 5. 生成 token（支持 remember_me）
    access_token, refresh_token, expires_in = create_tokens(user.id, login_req.remember_me)

    return AuthResponse(
        user_id=user.id,
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in
    )


@router.post("/sms-login", response_model=AuthResponse)
async def sms_login(sms_req: SmsLoginRequest, db: AsyncSession = Depends(get_db)):
    """
    手机验证码登录
    """
    # 0. 检查登录锁定状态
    _check_login_attempt(sms_req.phone)

    # 1. 验证验证码（带有效期检查）
    if not _verify_sms_code(sms_req.phone, sms_req.code):
        _record_failed_attempt(sms_req.phone)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="验证码错误或已过期"
        )

    # 2. 清除已使用的验证码
    del _sms_codes[sms_req.phone]

    # 3. 查找或创建用户
    result = await db.execute(select(User).where(User.phone == sms_req.phone))
    user = result.scalar_one_or_none()

    if not user:
        # 演示模式：自动创建用户（生产环境可要求先注册）
        new_user = User(
            username=f"user_{sms_req.phone[-4:]}",
            phone=sms_req.phone,
            hashed_password=hash_password("")  # 短信登录用户无密码
        )
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        user = new_user

    # 4. 检查用户状态
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用"
        )

    # 5. 清除登录尝试记录
    _clear_login_attempt(sms_req.phone)

    # 6. 生成 token
    access_token, refresh_token, expires_in = create_tokens(user.id)

    return AuthResponse(
        user_id=user.id,
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in
    )


@router.post("/send-code", response_model=SendCodeResponse)
async def send_sms_code(send_req: SendCodeRequest):
    """
    发送短信验证码
    演示模式：返回验证码供测试
    生产环境：调用短信网关（阿里云、腾讯云等）
    """
    # 演示模式：生成并存储验证码（5分钟有效期）
    code = generate_sms_code()
    _store_sms_code(send_req.phone, code)

    # TODO: 生产环境调用短信网关
    # await sms_gateway.send(phone=send_req.phone, template_id="xxx", params={"code": code})

    return SendCodeResponse(
        message="验证码已发送",
        code=code  # 演示模式下返回验证码
    )


@router.post("/refresh", response_model=AuthResponse)
async def refresh_token(refresh_token: str, db: AsyncSession = Depends(get_db)):
    """
    使用 refresh_token 刷新 access_token
    """
    # 1. 验证 refresh_token
    payload = decode_token(refresh_token)

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的 refresh token"
        )

    user_id = payload.get("sub")

    # 2. 检查用户是否存在
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在或已被禁用"
        )

    # 3. 生成新 token
    access_token, new_refresh_token, expires_in = create_tokens(user.id)

    return AuthResponse(
        user_id=user.id,
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=expires_in
    )
