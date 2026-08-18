from datetime import datetime, timedelta, timezone
from typing import Any
import bcrypt
import jwt

from app.core.config import settings

ALGORITHM = "HS256"


def get_password_hash(password: str) -> str:
    """Hash a raw password string using bcrypt."""
    pwd_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain text password against a bcrypt hash."""
    plain_bytes = plain_password.encode("utf-8")
    hashed_bytes = hashed_password.encode("utf-8")
    return bcrypt.checkpw(plain_bytes, hashed_bytes)


def create_access_token(subject: Any, role: str, expires_delta: timedelta | None = None) -> str:
    """Generate a JWT access token.
    
    Args:
        subject: The subject of the token (typically User UUID).
        role: The role classification of the user.
        expires_delta: Optional expiry duration override.
        
    Returns:
        The encoded JWT token string.
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {
        "sub": str(subject),
        "role": role,
        "exp": int(expire.timestamp())
    }
    
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> dict[str, Any] | None:
    """Decode and validate a JWT access token.
    
    Returns:
        The payload dict if valid, None if expired or invalid.
    """
    try:
        # Decodes token and verifies signature & expiration automatically
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None
