from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DB
from app.core.security import create_access_token, verify_password
from app.models.models import AuditLog, User
from app.schemas.schemas import LoginRequest, TokenResponse, UserRead

logger = structlog.get_logger()
router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(request: Request, body: LoginRequest, db: DB):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account deactivated")

    user.last_login = datetime.now(timezone.utc)
    db.add(user)

    log = AuditLog(user_id=user.id, action="login", resource="auth")
    db.add(log)
    await db.commit()

    token = create_access_token(subject=user.id)
    logger.info("user_login", user_id=user.id, email=user.email)
    return TokenResponse(access_token=token, user=UserRead.model_validate(user))


@router.get("/me", response_model=UserRead)
async def me(current_user: CurrentUser):
    return UserRead.model_validate(current_user)


@router.post("/logout")
async def logout(current_user: CurrentUser, db: DB):
    log = AuditLog(user_id=current_user.id, action="logout", resource="auth")
    db.add(log)
    await db.commit()
    return {"message": "Logged out"}
