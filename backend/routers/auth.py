"""
Simple JWT auth — single admin user configured via env vars.
No bcrypt dependency (uses constant-time comparison instead).
"""

import os
import hmac
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from pydantic import BaseModel

router = APIRouter(prefix="/api/auth", tags=["auth"])
security = HTTPBearer(auto_error=False)

# ── Config from env / .env ───────────────────────────────
ADMIN_USER = os.environ.get("LOGIN_USERNAME", "admin")
ADMIN_PASS = os.environ.get("LOGIN_PASSWORD", "admin123")
SECRET_KEY = os.environ.get("JWT_SECRET", "change-me-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480  # 8 hours


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = ACCESS_TOKEN_EXPIRE_MINUTES * 60


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest):
    """Authenticate and receive a JWT token."""
    if body.username != ADMIN_USER:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Constant-time compare to prevent timing attacks (no bcrypt dependency)
    if not hmac.compare_digest(body.password, ADMIN_PASS):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token = jwt.encode(
        {"sub": body.username, "exp": expire, "iat": datetime.now(timezone.utc)},
        SECRET_KEY,
        algorithm=ALGORITHM,
    )
    return TokenResponse(access_token=token)


def require_auth(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    """FastAPI dependency — protects routes that need a valid token."""
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub", "unknown")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
