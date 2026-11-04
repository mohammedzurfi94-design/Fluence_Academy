from fastapi import Request, HTTPException, status, Depends
from jose import jwt, JWTError
from sqlalchemy import select
from typing import Optional

from app.core.config import settings
from app.core.security import ALGORITHM
from app.database.connection import AsyncSessionLocal
from app.database.models import User

async def get_current_user_from_cookie(request: Request) -> Optional[User]:
    """Retrieves authenticated user from session cookie."""
    token = request.cookies.get("fluence_access_token")
    if not token:
        return None

    try:
        payload = jwt.decode(token, settings.APP_SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if not username:
            return None
    except JWTError:
        return None

    async with AsyncSessionLocal() as session:
        query = select(User).where(User.username == username, User.is_active == True)
        result = await session.execute(query)
        user = result.scalar_one_or_none()

    return user

async def require_admin_or_teacher(request: Request) -> User:
    """Dependency that ensures the user is logged in as an Admin or Teacher."""
    user = await get_current_user_from_cookie(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Location": "/login"}
        )
    if user.role not in ["admin", "teacher"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: Admin or Teacher role required."
        )
    return user
