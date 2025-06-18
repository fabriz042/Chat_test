"""
Simulación de Celery worker para tareas asíncronas
"""
import os
import time
import random
import logging
from datetime import datetime, timedelta

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("celery_worker")

# Simular conexión a Redis (broker)
def connect_to_broker():
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = int(os.getenv("REDIS_PORT", 6379))
    logger.info(f"Conectando a Redis broker en {redis_host}:{redis_port}")
    # Simulación de conexión
    time.sleep(1)
    return True

# Simular conexión a la base de datos
def connect_to_database():
    db_url = os.getenv("DATABASE_URL", "postgres://user:pass@localhost:5432/db")
    logger.info(f"Conectando a base de datos: {db_url}")
    # Simulación de conexión
    time.sleep(1)
    return True

# Tareas simuladas
class Tasks:
    @staticmethod
    def send_notification(user_id, message):
        logger.info(f"Enviando notificación a usuario {user_id}: {message}")
        # Simular procesamiento
        time.sleep(random.uniform(0.5, 2.0))
        return True

    @staticmethod
    def generate_report(report_type, date_range, filters=None):
        logger.info(f"Generando reporte {report_type} para {date_range}")
        # Simular generación de reporte
        time.sleep(random.uniform(3.0, 8.0))
        return {
            "report_id": random.randint(1000, 9999),
            "report_type": report_type,
            "generated_at": datetime.now().isoformat(),
            "size": f"{random.randint(100, 5000)} KB"
        }

    @staticmethod
    def sync_external_data(source, since=None):
        logger.info(f"Sincronizando datos desde {source}")
        # Simular sincronización
        time.sleep(random.uniform(2.0, 10.0))
        return {
            "records_processed": random.randint(10, 1000),
            "success": True,
            "duration": f"{random.uniform(2.0, 10.0):.2f} segundos"
        }

    @staticmethod
    def clean_old_data(days=30):
        logger.info(f"Limpiando datos con más de {days} días")
        # Simular limpieza
        time.sleep(random.uniform(1.0, 5.0))
        return {
            "records_removed": random.randint(0, 500),
            "space_freed": f"{random.uniform(0.1, 50.0):.2f} MB"
        }

# Simulación de worker de Celery
def run_worker():
    logger.info("Iniciando Celery worker")
    
    # Conectar a servicios
    broker_connected = connect_to_broker()
    db_connected = connect_to_database()
    
    if not broker_connected or not db_connected:
        logger.error("Error conectando a servicios requeridos")
        return False
    
    logger.info("Worker iniciado y esperando tareas")
    
    # Simular procesamiento de tareas
    tasks = Tasks()
    
    while True:
        # Simular recepción de tareas
        task_chance = random.random()
        
        if task_chance < 0.3:
            # Tarea de notificación
            user_id = random.randint(1, 100)
            messages = [
                "Nueva asignación de caso",
                "Actualización en caso #12345",
                "Reunión programada para mañana",
                "Alerta de seguridad en sector norte"
            ]
            tasks.send_notification(user_id, random.choice(messages))
            
        elif task_chance < 0.5:
            # Tarea de reporte
            report_types = ["actividad_diaria", "estadisticas_crimenes", "rendimiento_oficiales"]
            date_range = f"{(datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')} a {datetime.now().strftime('%Y-%m-%d')}"
            tasks.generate_report(random.choice(report_types), date_range)
            
        elif task_chance < 0.6:
            # Tarea de sincronización
            sources = ["sistema_nacional", "base_regional", "registro_civil"]
            tasks.sync_external_data(random.choice(sources))
            
        elif task_chance < 0.7:
            # Tarea de limpieza
            tasks.clean_old_data(days=random.choice([15, 30, 60, 90]))
        
        # Esperar antes de la siguiente iteración
        time.sleep(random.uniform(5, 15))

if __name__ == "__main__":
    try:
        run_worker()
    except KeyboardInterrupt:
        logger.info("Worker detenido por el usuario")
    except Exception as e:
        logger.error(f"Error en worker: {e}")
