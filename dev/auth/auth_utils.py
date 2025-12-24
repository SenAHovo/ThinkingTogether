# dev/auth/auth_utils.py
"""
用户认证工具模块
提供JWT令牌生成、密码哈希、用户认证等功能
"""
from __future__ import annotations

import os
import uuid
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import jwt

# JWT 配置
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7天
REFRESH_TOKEN_EXPIRE_DAYS = 30


def hash_password(password: str) -> str:
    """使用SHA256哈希密码"""
    # 在实际生产中应该使用 bcrypt 或 argon2，这里使用 SHA256 简化实现
    salt = "thinking-together-salt-2024"
    return hashlib.sha256(f"{password}{salt}".encode()).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    """验证密码"""
    return hash_password(password) == password_hash


def create_access_token(user_id: str, username: str, role: str) -> str:
    """创建访问令牌"""
    payload = {
        "user_id": user_id,
        "username": username,
        "role": role,
        "type": "access",
        "exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    """创建刷新令牌"""
    payload = {
        "user_id": user_id,
        "type": "refresh",
        "exp": datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """解码令牌"""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def generate_user_id() -> str:
    """生成用户ID"""
    return uuid.uuid4().hex[:32]


def generate_session_id() -> str:
    """生成会话ID"""
    return uuid.uuid4().hex[:64]
