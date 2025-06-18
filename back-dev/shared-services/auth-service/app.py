"""
Servicio de Autenticación para SmartPoli
Gestiona autenticación, autorización y tokens JWT
"""
import os
import time
import json
import uuid
import logging
import datetime
import secrets
import jwt
from typing import Dict, List, Optional, Union, Any
from fastapi import FastAPI, HTTPException, Depends, status, Header, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
import redis
import uvicorn

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("auth_service")

# Inicializar aplicación
app = FastAPI(title="SmartPoli Auth Service", 
              description="Servicio de autenticación y autorización para SmartPoli", 
              version="1.0.0")

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuraciones
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
JWT_SECRET = os.getenv("JWT_SECRET", "super-secret-jwt-key-for-development-only")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION = 3600  # 1 hora

# Conexión a Redis
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)

# Esquema OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Modelos de datos
class User(BaseModel):
    id: Optional[str] = None
    username: str
    email: EmailStr
    full_name: str
    role: str
    department: Optional[str] = None
    disabled: bool = False

class UserInDB(User):
    hashed_password: str
    created_at: datetime.datetime = datetime.datetime.now()
    last_login: Optional[datetime.datetime] = None

class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    user_id: str
    role: str

class TokenData(BaseModel):
    user_id: str
    role: str
    exp: int

# Función para simular hash de contraseña (en producción usar bcrypt o similar)
def get_password_hash(password):
    return f"hashed_{password}_salt"

def verify_password(plain_password, hashed_password):
    return hashed_password == get_password_hash(plain_password)

# Funciones de autenticación
def get_user(username: str) -> Optional[UserInDB]:
    """Obtener usuario de Redis o simulación"""
    try:
        user_data = redis_client.get(f"user:{username}")
        if user_data and isinstance(user_data, (str, bytes)):
            if isinstance(user_data, bytes):
                user_data = user_data.decode('utf-8')
            return UserInDB(**json.loads(user_data))
    except Exception as e:
        logger.error(f"Error getting user from Redis: {e}")
    
    # Usuarios simulados para desarrollo
    fake_users_db = {
        "admin": {
            "id": "usr_001",
            "username": "admin",
            "email": "admin@smartpoli.gov",
            "full_name": "Administrador del Sistema",
            "role": "admin",
            "department": "IT",
            "disabled": False,
            "hashed_password": get_password_hash("admin123"),
            "created_at": "2025-01-01T00:00:00",
            "last_login": None
        },
        "officer": {
            "id": "usr_002",
            "username": "officer",
            "email": "officer@smartpoli.gov",
            "full_name": "Oficial Modelo",
            "role": "officer",
            "department": "Patrol",
            "disabled": False,
            "hashed_password": get_password_hash("officer123"),
            "created_at": "2025-01-02T00:00:00",
            "last_login": None
        },
        "detective": {
            "id": "usr_003",
            "username": "detective",
            "email": "detective@smartpoli.gov",
            "full_name": "Detective Ejemplo",
            "role": "detective",
            "department": "Investigation",
            "disabled": False,
            "hashed_password": get_password_hash("detective123"),
            "created_at": "2025-01-03T00:00:00",
            "last_login": None
        }
    }
    
    if username in fake_users_db:
        return UserInDB(**fake_users_db[username])
    return None

def authenticate_user(username: str, password: str) -> Optional[UserInDB]:
    """Autenticar usuario"""
    user = get_user(username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

def create_jwt_token(data: dict) -> str:
    """Crear token JWT"""
    to_encode = data.copy()
    expire = datetime.datetime.now() + datetime.timedelta(seconds=JWT_EXPIRATION)
    to_encode.update({"exp": expire.timestamp()})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """Validar token y obtener usuario actual"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("user_id")
        role = payload.get("role")
        if user_id is None or role is None:
            raise credentials_exception
        token_data = TokenData(user_id=user_id, role=role, exp=payload.get("exp"))
    except jwt.PyJWTError:
        raise credentials_exception
    
    # Obtener usuario por ID (simulado)
    user = None
    for u in [get_user("admin"), get_user("officer"), get_user("detective")]:
        if u and u.id == token_data.user_id:
            user = u
            break
    
    if user is None:
        raise credentials_exception
    if user.disabled:
        raise HTTPException(status_code=400, detail="Usuario inactivo")
    return user

# Rutas de autenticación
@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """Iniciar sesión y obtener token JWT"""
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Actualizar último login
    user.last_login = datetime.datetime.now()
    try:
        redis_client.set(f"user:{user.username}", json.dumps(user.dict()))
    except Exception as e:
        logger.error(f"Error updating user in Redis: {e}")
    
    token_data = {
        "user_id": user.id,
        "role": user.role,
        "sub": user.username
    }
    
    access_token = create_jwt_token(token_data)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": JWT_EXPIRATION,
        "user_id": user.id,
        "role": user.role
    }

@app.get("/users/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """Obtener datos del usuario actual"""
    return current_user

@app.get("/users/me/permissions")
async def read_user_permissions(current_user: User = Depends(get_current_user)):
    """Obtener permisos del usuario actual basados en su rol"""
    role_permissions = {
        "admin": [
            "users:read", "users:write", "users:delete",
            "cases:read", "cases:write", "cases:delete",
            "reports:read", "reports:write", "reports:delete",
            "settings:read", "settings:write"
        ],
        "detective": [
            "users:read",
            "cases:read", "cases:write",
            "reports:read", "reports:write"
        ],
        "officer": [
            "users:read",
            "cases:read",
            "reports:read"
        ]
    }
    
    return {
        "user_id": current_user.id,
        "role": current_user.role,
        "permissions": role_permissions.get(current_user.role, [])
    }

@app.post("/logout")
async def logout(token: str = Depends(oauth2_scheme)):
    """Cerrar sesión (invalidar token)"""
    try:
        # En una implementación real, agregaríamos el token a una lista negra en Redis
        # para invalidarlo antes de su expiración natural
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        jti = payload.get("jti", "")
        exp = payload.get("exp", 0)
        
        # Tiempo restante para expiración
        current_time = datetime.datetime.now().timestamp()
        ttl = max(0, int(exp - current_time))
        
        if jti and ttl > 0:
            redis_client.setex(f"blacklist:{jti}", ttl, "1")
            
        return {"message": "Sesión cerrada exitosamente"}
    except Exception as e:
        logger.error(f"Error during logout: {e}")
        return {"message": "Sesión cerrada exitosamente"}

@app.post("/users", status_code=status.HTTP_201_CREATED, response_model=User)
async def create_user(user_data: User, current_user: User = Depends(get_current_user)):
    """Crear un nuevo usuario (solo admin)"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo administradores pueden crear usuarios"
        )
    
    # Generar ID único
    user_data.id = f"usr_{uuid.uuid4().hex[:8]}"
    
    # En una implementación real, verificaríamos que el username/email no existan
    # y manejaríamos el hash de la contraseña
    
    return user_data

@app.get("/health")
async def health_check():
    """Verificar estado del servicio"""
    return {
        "status": "healthy",
        "service": "auth",
        "timestamp": datetime.datetime.now().isoformat()
    }

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
