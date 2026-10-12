from __future__ import annotations

import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from db.models import User, Workspace
from db.session import get_db
from services.auth import create_access_token, decode_access_token, hash_password, verify_password

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters")
    full_name: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class GoogleAuthRequest(BaseModel):
    email: EmailStr
    full_name: str | None = None
    avatar_url: str | None = None
    credential: str | None = None


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)


class UserOut(BaseModel):
    id: str
    email: str
    full_name: str | None = None
    avatar_url: str | None = None
    auth_provider: str


class WorkspaceOut(BaseModel):
    id: str
    name: str
    api_key: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
    workspace: WorkspaceOut


def _get_or_create_default_workspace(user: User, db: Session) -> Workspace:
    """Ensure a user has at least one workspace."""
    ws = db.query(Workspace).filter(Workspace.user_id == user.id).first()
    if not ws:
        ws_name = f"{user.full_name or 'Personal'}'s Workspace"
        api_key = f"nx_{secrets.token_urlsafe(24)}"
        ws = Workspace(
            user_id=user.id,
            name=ws_name,
            api_key=api_key,
        )
        db.add(ws)
        db.commit()
        db.refresh(ws)
    return ws


def _to_user_out(user: User) -> UserOut:
    return UserOut(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        avatar_url=user.avatar_url,
        auth_provider=user.auth_provider,
    )


def _to_ws_out(ws: Workspace) -> WorkspaceOut:
    return WorkspaceOut(
        id=str(ws.id),
        name=ws.name,
        api_key=ws.api_key,
    )


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    email_clean = req.email.lower().strip()
    existing = db.query(User).filter(User.email == email_clean).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists.",
        )

    # Password complexity check: require at least one number or letter combination
    if not any(c.isdigit() for c in req.password) and not any(not c.isalnum() for c in req.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one number or special character.",
        )

    user = User(
        email=email_clean,
        full_name=req.full_name.strip() if req.full_name else email_clean.split("@")[0].capitalize(),
        hashed_password=hash_password(req.password),
        auth_provider="email",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    ws = _get_or_create_default_workspace(user, db)
    token = create_access_token({"sub": str(user.id), "email": user.email})

    logger.info("New user registered: %s (id=%s)", user.email, user.id)
    return AuthResponse(
        access_token=token,
        user=_to_user_out(user),
        workspace=_to_ws_out(ws),
    )


@router.post("/login", response_model=AuthResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    email_clean = req.email.lower().strip()
    user = db.query(User).filter(User.email == email_clean).first()
    if not user or not user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive. Please contact support.",
        )

    ws = _get_or_create_default_workspace(user, db)
    token = create_access_token({"sub": str(user.id), "email": user.email})

    logger.info("User logged in: %s", user.email)
    return AuthResponse(
        access_token=token,
        user=_to_user_out(user),
        workspace=_to_ws_out(ws),
    )


@router.post("/google", response_model=AuthResponse)
def google_auth(req: GoogleAuthRequest, db: Session = Depends(get_db)):
    email_clean = req.email.lower().strip()
    user = db.query(User).filter(User.email == email_clean).first()
    if not user:
        user = User(
            email=email_clean,
            full_name=req.full_name or email_clean.split("@")[0].capitalize(),
            avatar_url=req.avatar_url,
            auth_provider="google",
            hashed_password=None,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info("Google user registered: %s", user.email)
    else:
        if req.avatar_url and not user.avatar_url:
            user.avatar_url = req.avatar_url
            db.commit()

    ws = _get_or_create_default_workspace(user, db)
    token = create_access_token({"sub": str(user.id), "email": user.email})

    return AuthResponse(
        access_token=token,
        user=_to_user_out(user),
        workspace=_to_ws_out(ws),
    )


@router.post("/forgot-password")
def forgot_password(req: ForgotPasswordRequest, db: Session = Depends(get_db)):
    email_clean = req.email.lower().strip()
    user = db.query(User).filter(User.email == email_clean).first()
    if user:
        reset_token = secrets.token_urlsafe(32)
        user.reset_token = reset_token
        user.reset_token_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        db.commit()
        logger.info("Password reset requested for %s: token=%s", user.email, reset_token)
        return {
            "ok": True,
            "message": "Password reset instructions have been sent to your email.",
            "demo_reset_token": reset_token,
        }
    return {
        "ok": True,
        "message": "If an account exists with this email, reset instructions have been sent.",
    }


@router.post("/reset-password")
def reset_password(req: ResetPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.reset_token == req.token).first()
    if not user or not user.reset_token_expires_at:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token.")

    if user.reset_token_expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Reset token has expired.")

    user.hashed_password = hash_password(req.new_password)
    user.reset_token = None
    user.reset_token_expires_at = None
    db.commit()

    return {"ok": True, "message": "Password successfully updated. You may now log in."}


@router.get("/me", response_model=AuthResponse)
def get_current_user(
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authentication token.",
        )
    token = authorization.split(" ")[1]
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has expired or is invalid.",
        )

    user_id = payload["sub"]
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=404, detail="User not found or inactive.")

    ws = _get_or_create_default_workspace(user, db)
    return AuthResponse(
        access_token=token,
        user=_to_user_out(user),
        workspace=_to_ws_out(ws),
    )
