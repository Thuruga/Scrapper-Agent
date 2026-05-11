from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from config import settings

# Configuração de Hashing de Senhas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# auto_error=False permite que a rota não falhe imediatamente quando o header está ausente,
# possibilitando o fallback via query param (necessário para WebSockets)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login", auto_error=False)

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    token_query: Optional[str] = None
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Se o token não veio via header (OAuth2), tenta via query param (útil para WS)
    final_token = token if token else token_query
    
    if not final_token:
        raise credentials_exception

    try:
        payload = jwt.decode(final_token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    
    if token_data.username != settings.ADMIN_USER:
        raise credentials_exception
        
    return token_data.username

# Mantemos suporte a API Key se necessário, ou podemos migrar tudo para get_current_user
def get_api_key(api_key: str = None):
    # Fallback para o comportamento antigo se necessário, 
    # mas o dashboard usará JWT
    if api_key == settings.SCRAPER_API_KEY:
        return api_key
    raise HTTPException(status_code=403, detail="Acesso negado")
