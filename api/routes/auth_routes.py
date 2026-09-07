"""Authentication endpoints."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from api.auth import USERS_DB, verify_password, create_access_token, pwd_context

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login")
async def login(request: "LoginRequest"):
    """Login and receive JWT token."""
    user = USERS_DB.get(request.username)
    if not user or not verify_password(request.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_access_token(
        {"sub": user["username"], "role": user["role"]}
    )
    return {"access_token": token, "token_type": "bearer"}


@router.post("/register")
async def register(request: "RegisterRequest"):
    """Register a new user (admin only in production)."""
    if request.username in USERS_DB:
        raise HTTPException(status_code=409, detail="User already exists")
    USERS_DB[request.username] = {
        "username": request.username,
        "hashed_password": pwd_context.hash(request.password),
        "role": request.role,
    }
    return {"ok": True, "username": request.username}


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str
    role: str = "viewer"