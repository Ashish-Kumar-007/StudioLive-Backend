from typing import Annotated
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import UnauthorizedException, ForbiddenException
from app.core.security import decode_token
from app.db.session import get_db
from app.modules.users.models import User

# HTTPBearer security scheme
security = HTTPBearer()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: AsyncSession = Depends(get_db)
) -> User:
    """FastAPI dependency to authenticate and resolve the current session user."""
    token = credentials.credentials
    payload = decode_token(token)
    
    if not payload:
        raise UnauthorizedException(
            message="Your session has expired or the token is invalid.",
            code="TOKEN_INVALID"
        )
        
    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedException(
            message="Invalid token payload: missing subject identifier.",
            code="TOKEN_MALFORMED"
        )
        
    # Fetch user from database
    result = await db.execute(select(User).filter_by(id=user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise UnauthorizedException(
            message="User session not found in system registers.",
            code="USER_NOT_FOUND"
        )
        
    if not user.is_active:
        raise ForbiddenException(
            message="This user account has been deactivated.",
            code="USER_INACTIVE"
        )
        
    return user


class require_roles:
    """RBAC dependency class to restrict endpoints based on user roles."""
    
    def __init__(self, allowed_roles: list[str]) -> None:
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in self.allowed_roles:
            raise ForbiddenException(
                message=f"Access denied: role must be one of {self.allowed_roles}.",
                code="ROLE_PERMISSION_DENIED"
            )
        return current_user
