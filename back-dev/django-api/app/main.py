"""
Simulación de Django API usando FastAPI
"""
import os
from typing import Dict, List, Optional
from datetime import datetime
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import redis
import json

# Inicializar aplicación
app = FastAPI(title="SmartPoli API", description="API de gestión policial", version="1.0.0")

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Conexión a Redis
redis_host = os.getenv("REDIS_HOST", "localhost")
redis_port = int(os.getenv("REDIS_PORT", 6379))
redis_client = redis.Redis(host=redis_host, port=redis_port, db=0)

# Modelos de datos
class Officer(BaseModel):
    id: Optional[int] = None
    badge_number: str
    name: str
    rank: str
    department: str
    active: bool = True

class Case(BaseModel):
    id: Optional[int] = None
    case_number: str
    title: str
    description: str
    status: str
    assigned_to: List[int]
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()

# Rutas para oficiales
@app.get("/api/officers/", response_model=List[Officer])
def get_officers():
    """Listar todos los oficiales"""
    try:
        officers_data = redis_client.get("officers")
        if not officers_data:
            return []
        return json.loads(officers_data)
    except:
        # Simulación fallback
        return [
            {"id": 1, "badge_number": "12345", "name": "John Doe", "rank": "Detective", "department": "Homicide", "active": True},
            {"id": 2, "badge_number": "67890", "name": "Jane Smith", "rank": "Officer", "department": "Patrol", "active": True},
        ]

@app.post("/api/officers/", response_model=Officer, status_code=status.HTTP_201_CREATED)
def create_officer(officer: Officer):
    """Crear un nuevo oficial"""
    try:
        # Simulación de ID autogenerado
        officers_data = redis_client.get("officers")
        officers = json.loads(officers_data) if officers_data else []
        
        new_id = max([o.get("id", 0) for o in officers], default=0) + 1
        officer.id = new_id
        
        officers.append(officer.dict())
        redis_client.set("officers", json.dumps(officers))
        return officer
    except:
        # Simulación sin Redis
        officer.id = 3  # Simulado
        return officer

# Rutas para casos
@app.get("/api/cases/", response_model=List[Case])
def get_cases():
    """Listar todos los casos"""
    try:
        cases_data = redis_client.get("cases")
        if not cases_data:
            return []
        return json.loads(cases_data)
    except:
        # Simulación fallback
        return [
            {
                "id": 1, 
                "case_number": "CP-2025-001", 
                "title": "Robo en tienda", 
                "description": "Robo reportado en tienda central",
                "status": "Abierto",
                "assigned_to": [1, 2],
                "created_at": "2025-06-15T10:30:00",
                "updated_at": "2025-06-15T10:30:00"
            }
        ]

@app.post("/api/cases/", response_model=Case, status_code=status.HTTP_201_CREATED)
def create_case(case: Case):
    """Crear un nuevo caso"""
    try:
        # Simulación de ID autogenerado
        cases_data = redis_client.get("cases")
        cases = json.loads(cases_data) if cases_data else []
        
        new_id = max([c.get("id", 0) for c in cases], default=0) + 1
        case.id = new_id
        
        cases.append(case.dict())
        redis_client.set("cases", json.dumps(cases))
        return case
    except:
        # Simulación sin Redis
        case.id = 2  # Simulado
        return case

# Ruta para estadísticas
@app.get("/api/stats/")
def get_stats():
    """Obtener estadísticas del sistema"""
    return {
        "total_officers": 25,
        "active_officers": 23,
        "total_cases": 156,
        "open_cases": 42,
        "cases_this_month": 15,
        "response_time_avg": "45 minutos"
    }

# Ruta para healthcheck
@app.get("/health")
def health_check():
    """Verificar estado de la API"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# Ruta para admin (simulación de Django admin)
@app.get("/admin/login/")
def admin_login():
    """Simulación de página de login del admin"""
    return {"message": "Admin login page"}

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
