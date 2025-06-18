"""
Servicio de Correo para SmartPoli
Gestiona el envío de correos electrónicos transaccionales y notificaciones
"""
import os
import time
import json
import uuid
import logging
import datetime
from typing import Dict, List, Optional, Union, Any
from fastapi import FastAPI, HTTPException, Depends, status, Header, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
import redis
import jwt
import uvicorn
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("email_service")

# Inicializar aplicación
app = FastAPI(title="SmartPoli Email Service", 
              description="Servicio de correo electrónico para SmartPoli", 
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
REDIS_DB = int(os.getenv("REDIS_DB", 1))  # Diferente DB que auth
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.example.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER", "notifications@smartpoli.gov")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "email-password-placeholder")
EMAIL_FROM = os.getenv("EMAIL_FROM", "SmartPoli <notifications@smartpoli.gov>")
JWT_SECRET = os.getenv("JWT_SECRET", "super-secret-jwt-key-for-development-only")
JWT_ALGORITHM = "HS256"

# Conexión a Redis para cola de correos y tracking
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)

# Modelos de datos
class EmailTemplate(BaseModel):
    id: str
    name: str
    subject: str
    html_content: str
    text_content: str

class EmailRecipient(BaseModel):
    email: EmailStr
    name: Optional[str] = None

class EmailAttachment(BaseModel):
    filename: str
    content_type: str
    data: str  # Base64 encoded

class EmailRequest(BaseModel):
    template_id: str
    recipients: List[EmailRecipient]
    cc: Optional[List[EmailRecipient]] = None
    bcc: Optional[List[EmailRecipient]] = None
    reply_to: Optional[str] = None
    template_data: Optional[Dict[str, str]] = None
    attachments: Optional[List[EmailAttachment]] = None
    priority: str = Field(default="normal", description="Priority: high, normal, low")
    tracking_id: Optional[str] = None

class EmailResponse(BaseModel):
    success: bool
    message: str
    email_id: str
    tracking_id: Optional[str] = None
    queued_at: datetime.datetime

class EmailStatus(BaseModel):
    email_id: str
    tracking_id: Optional[str] = None
    status: str  # queued, sent, delivered, opened, failed
    error: Optional[str] = None
    updated_at: datetime.datetime

# Templates simulados
TEMPLATES = {
    "welcome": EmailTemplate(
        id="welcome",
        name="Welcome Email",
        subject="Bienvenido a SmartPoli",
        html_content="""
        <html>
        <body>
            <h1>Bienvenido a SmartPoli, {{name}}!</h1>
            <p>Tu cuenta ha sido creada exitosamente.</p>
            <p>Tu usuario es: <strong>{{username}}</strong></p>
            <p>Para iniciar sesión, visita: <a href="{{login_url}}">Portal SmartPoli</a></p>
        </body>
        </html>
        """,
        text_content="""
        Bienvenido a SmartPoli, {{name}}!
        
        Tu cuenta ha sido creada exitosamente.
        Tu usuario es: {{username}}
        
        Para iniciar sesión, visita: {{login_url}}
        """
    ),
    "password_reset": EmailTemplate(
        id="password_reset",
        name="Password Reset",
        subject="Restablecimiento de contraseña SmartPoli",
        html_content="""
        <html>
        <body>
            <h1>Restablecimiento de contraseña</h1>
            <p>Hola {{name}},</p>
            <p>Has solicitado restablecer tu contraseña. Haz clic en el siguiente enlace para continuar:</p>
            <p><a href="{{reset_url}}">Restablecer contraseña</a></p>
            <p>Este enlace expirará en 1 hora.</p>
            <p>Si no solicitaste este cambio, ignora este correo.</p>
        </body>
        </html>
        """,
        text_content="""
        Restablecimiento de contraseña
        
        Hola {{name}},
        
        Has solicitado restablecer tu contraseña. Visita la siguiente URL para continuar:
        {{reset_url}}
        
        Este enlace expirará en 1 hora.
        
        Si no solicitaste este cambio, ignora este correo.
        """
    ),
    "case_update": EmailTemplate(
        id="case_update",
        name="Case Update",
        subject="Actualización de caso #{{case_id}}",
        html_content="""
        <html>
        <body>
            <h1>Actualización de caso #{{case_id}}</h1>
            <p>Hola {{name}},</p>
            <p>El caso #{{case_id}} ha sido actualizado:</p>
            <p><strong>Estado:</strong> {{status}}</p>
            <p><strong>Actualizado por:</strong> {{updated_by}}</p>
            <p><strong>Comentarios:</strong> {{comments}}</p>
            <p>Para ver los detalles, <a href="{{case_url}}">haz clic aquí</a>.</p>
        </body>
        </html>
        """,
        text_content="""
        Actualización de caso #{{case_id}}
        
        Hola {{name}},
        
        El caso #{{case_id}} ha sido actualizado:
        
        Estado: {{status}}
        Actualizado por: {{updated_by}}
        Comentarios: {{comments}}
        
        Para ver los detalles, visita: {{case_url}}
        """
    ),
    "alert": EmailTemplate(
        id="alert",
        name="System Alert",
        subject="ALERTA: {{alert_type}}",
        html_content="""
        <html>
        <body>
            <h1>ALERTA: {{alert_type}}</h1>
            <p>Se ha detectado una alerta en el sistema:</p>
            <p><strong>Tipo:</strong> {{alert_type}}</p>
            <p><strong>Prioridad:</strong> {{priority}}</p>
            <p><strong>Detalles:</strong> {{details}}</p>
            <p><strong>Fecha/Hora:</strong> {{timestamp}}</p>
        </body>
        </html>
        """,
        text_content="""
        ALERTA: {{alert_type}}
        
        Se ha detectado una alerta en el sistema:
        
        Tipo: {{alert_type}}
        Prioridad: {{priority}}
        Detalles: {{details}}
        Fecha/Hora: {{timestamp}}
        """
    )
}

# Funciones de autenticación y autorización
async def verify_service_token(authorization: Optional[str] = Header(None)):
    """Verificar token de servicio"""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No se proporcionó token de autenticación",
        )
    
    try:
        # Extraer token Bearer
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido",
            )
        
        # Verificar JWT
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except Exception as e:
        logger.error(f"Error al verificar token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
        )

# Funciones de procesamiento de correos
def process_template(template: EmailTemplate, data: Dict[str, str]) -> Dict[str, str]:
    """Procesar plantilla con los datos proporcionados"""
    subject = template.subject
    html_content = template.html_content
    text_content = template.text_content
    
    # Reemplazar variables en la plantilla
    for key, value in data.items():
        placeholder = "{{" + key + "}}"
        subject = subject.replace(placeholder, value)
        html_content = html_content.replace(placeholder, value)
        text_content = text_content.replace(placeholder, value)
    
    return {
        "subject": subject,
        "html_content": html_content,
        "text_content": text_content
    }

def decode_redis_hash(redis_hash: Dict[bytes, bytes]) -> Dict[str, str]:
    """Decodificar respuesta de Redis hash"""
    if not redis_hash:
        return {}
    return {k.decode('utf-8'): v.decode('utf-8') for k, v in redis_hash.items()}

def send_email_background(email_data: Dict[str, Any]):
    """Enviar correo en background (simulado)"""
    email_id = email_data.get("email_id")
    tracking_id = email_data.get("tracking_id")
    template_id = str(email_data.get("template_id", ""))
    recipients = email_data.get("recipients", [])
    template_data = email_data.get("template_data", {})
    
    try:
        # Actualizar estado a "processing"
        redis_client.hset(f"email:{email_id}", "status", "processing")
        redis_client.hset(f"email:{email_id}", "updated_at", datetime.datetime.now().isoformat())
        
        # Simular procesamiento
        logger.info(f"Procesando correo {email_id} usando plantilla {template_id}")
        time.sleep(1)  # Simular latencia
        
        # Obtener plantilla
        template = TEMPLATES.get(template_id)
        if not template:
            raise Exception(f"Plantilla {template_id} no encontrada")
        
        # Procesar plantilla
        processed = process_template(template, template_data)
        
        # Simular envío para cada destinatario
        for recipient in recipients:
            logger.info(f"Enviando correo a {recipient.get('email')}")
            time.sleep(0.5)  # Simular latencia por destinatario
        
        # Actualizar estado a "sent"
        redis_client.hset(f"email:{email_id}", "status", "sent")
        redis_client.hset(f"email:{email_id}", "updated_at", datetime.datetime.now().isoformat())
        
        # Si hay ID de tracking, registrar para seguimiento
        if tracking_id:
            redis_client.hset(f"tracking:{tracking_id}", "email_id", email_id)
            redis_client.hset(f"tracking:{tracking_id}", "status", "sent")
            redis_client.hset(f"tracking:{tracking_id}", "updated_at", datetime.datetime.now().isoformat())
        
        logger.info(f"Correo {email_id} enviado exitosamente")
    except Exception as e:
        # Registrar error
        error_msg = str(e)
        logger.error(f"Error al enviar correo {email_id}: {error_msg}")
        redis_client.hset(f"email:{email_id}", "status", "failed")
        redis_client.hset(f"email:{email_id}", "error", error_msg)
        redis_client.hset(f"email:{email_id}", "updated_at", datetime.datetime.now().isoformat())
        
        if tracking_id:
            redis_client.hset(f"tracking:{tracking_id}", "status", "failed")
            redis_client.hset(f"tracking:{tracking_id}", "error", error_msg)
            redis_client.hset(f"tracking:{tracking_id}", "updated_at", datetime.datetime.now().isoformat())

# Rutas API
@app.post("/send", response_model=EmailResponse)
async def send_email(
    email_request: EmailRequest, 
    background_tasks: BackgroundTasks,
    payload: dict = Depends(verify_service_token)
):
    """Enviar correo electrónico utilizando una plantilla"""
    # Verificar que existe la plantilla
    template_id = email_request.template_id
    if template_id not in TEMPLATES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plantilla {template_id} no encontrada"
        )
    
    # Generar ID único para el correo
    email_id = f"email_{uuid.uuid4().hex}"
    tracking_id = email_request.tracking_id or f"track_{uuid.uuid4().hex[:10]}"
    
    # Crear datos del correo
    email_data = {
        "email_id": email_id,
        "tracking_id": tracking_id,
        "template_id": template_id,
        "recipients": [r.dict() for r in email_request.recipients],
        "cc": [r.dict() for r in email_request.cc] if email_request.cc else [],
        "bcc": [r.dict() for r in email_request.bcc] if email_request.bcc else [],
        "template_data": email_request.template_data or {},
        "status": "queued",
        "queued_at": datetime.datetime.now().isoformat(),
        "priority": email_request.priority,
        "sender_service": payload.get("service", "unknown"),
    }
    
    # Guardar en Redis
    redis_client.hmset(f"email:{email_id}", email_data)
    
    # Agregar a la cola según prioridad
    queue_key = f"email_queue:{email_request.priority}"
    redis_client.rpush(queue_key, email_id)
    
    # Procesar en background
    background_tasks.add_task(send_email_background, email_data)
    
    return EmailResponse(
        success=True,
        message="Correo en cola para envío",
        email_id=email_id,
        tracking_id=tracking_id,
        queued_at=datetime.datetime.now()
    )

@app.get("/status/{email_id}", response_model=EmailStatus)
async def get_email_status(
    email_id: str, 
    payload: dict = Depends(verify_service_token)
):
    """Obtener estado de un correo por su ID"""
    email_data = redis_client.hgetall(f"email:{email_id}")
    
    if not email_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Correo con ID {email_id} no encontrado"
        )
      # Convertir de bytes a string si es necesario
    if email_data:
        email_data_dict = {}
        for k, v in email_data.items():
            if isinstance(k, bytes):
                k = k.decode('utf-8')
            if isinstance(v, bytes):
                v = v.decode('utf-8')
            email_data_dict[k] = v
        email_data = email_data_dict
    
    return EmailStatus(
        email_id=email_id,
        tracking_id=email_data.get("tracking_id"),
        status=email_data.get("status", "unknown"),
        error=email_data.get("error"),
        updated_at=datetime.datetime.fromisoformat(
            email_data.get("updated_at") or email_data.get("queued_at") or datetime.datetime.now().isoformat()
        )
    )

@app.get("/tracking/{tracking_id}", response_model=EmailStatus)
async def get_tracking_status(
    tracking_id: str, 
    payload: dict = Depends(verify_service_token)
):
    """Obtener estado de un correo por su ID de seguimiento"""
    tracking_data = redis_client.hgetall(f"tracking:{tracking_id}")
    
    if not tracking_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Seguimiento con ID {tracking_id} no encontrado"
        )
    
    # Convertir de bytes a string
    tracking_data = {k.decode('utf-8'): v.decode('utf-8') for k, v in tracking_data.items()}
    
    # Obtener email_id asociado
    email_id = tracking_data.get("email_id")
    if not email_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Email ID no encontrado para el seguimiento {tracking_id}"
        )
    
    # Obtener datos del correo
    email_data = redis_client.hgetall(f"email:{email_id}")
    if not email_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Correo con ID {email_id} no encontrado"
        )
    
    # Convertir de bytes a string
    email_data = {k.decode('utf-8'): v.decode('utf-8') for k, v in email_data.items()}
    
    return EmailStatus(
        email_id=email_id,
        tracking_id=tracking_id,
        status=email_data.get("status", "unknown"),
        error=email_data.get("error"),
        updated_at=datetime.datetime.fromisoformat(email_data.get("updated_at", email_data.get("queued_at")))
    )

@app.get("/templates")
async def list_templates(payload: dict = Depends(verify_service_token)):
    """Listar plantillas disponibles"""
    return {
        "templates": [
            {"id": t_id, "name": template.name, "subject": template.subject}
            for t_id, template in TEMPLATES.items()
        ]
    }

@app.get("/templates/{template_id}")
async def get_template(template_id: str, payload: dict = Depends(verify_service_token)):
    """Obtener detalles de una plantilla"""
    if template_id not in TEMPLATES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plantilla {template_id} no encontrada"
        )
    
    return TEMPLATES[template_id]

@app.get("/health")
async def health_check():
    """Verificar estado del servicio"""
    return {
        "status": "healthy",
        "service": "email",
        "templates": len(TEMPLATES),
        "timestamp": datetime.datetime.now().isoformat()
    }

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8080, reload=True)
