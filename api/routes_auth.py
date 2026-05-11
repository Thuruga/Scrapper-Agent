from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from config import settings
from api.auth import create_access_token, verify_password, get_password_hash, get_current_user

router = APIRouter(tags=["Authentication"])

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    username: str

@router.post("/login", response_model=LoginResponse)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    # Validação simples contra as configurações (Usuário Admin Único)
    is_valid_user = form_data.username == settings.ADMIN_USER
    
    # Em um sistema real, verificaríamos contra o hash no banco.
    # Aqui, para simplicidade, verificamos contra a config.
    is_valid_pass = form_data.password == settings.ADMIN_PASS
    
    if not is_valid_user or not is_valid_pass:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": form_data.username}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "username": form_data.username
    }

@router.get("/me")
async def read_users_me(current_user: str = Depends(get_current_user)):
    return {"username": current_user}
