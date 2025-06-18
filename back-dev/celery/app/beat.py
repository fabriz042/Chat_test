"""
Simulación de Celery beat para tareas programadas
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
logger = logging.getLogger("celery_beat")

# Lista de tareas programadas
SCHEDULED_TASKS = [
    {
        "name": "daily_report_generation",
        "task": "generate_report",
        "schedule": "0 7 * * *",  # 7:00 AM diariamente
        "args": ["actividad_diaria", "últimas 24 horas"],
        "description": "Generar reporte diario de actividad"
    },
    {
        "name": "weekly_crime_stats",
        "task": "generate_report",
        "schedule": "0 9 * * 1",  # 9:00 AM los lunes
        "args": ["estadisticas_crimenes", "última semana"],
        "description": "Estadísticas semanales de crímenes"
    },
    {
        "name": "officer_performance_monthly",
        "task": "generate_report",
        "schedule": "0 8 1 * *",  # 8:00 AM el primer día del mes
        "args": ["rendimiento_oficiales", "último mes"],
        "description": "Reporte mensual de rendimiento de oficiales"
    },
    {
        "name": "external_data_sync",
        "task": "sync_external_data",
        "schedule": "0 */4 * * *",  # Cada 4 horas
        "args": ["sistema_nacional"],
        "description": "Sincronización con sistema nacional"
    },
    {
        "name": "database_cleanup",
        "task": "clean_old_data",
        "schedule": "0 2 * * 0",  # 2:00 AM los domingos
        "args": [90],  # 90 días
        "description": "Limpieza de datos antiguos"
    },
    {
        "name": "reminder_notifications",
        "task": "send_reminders",
        "schedule": "0 8 * * 1-5",  # 8:00 AM de lunes a viernes
        "args": [],
        "description": "Envío de recordatorios diarios"
    }
]

# Simular ejecución de beat
def run_beat():
    logger.info("Iniciando Celery beat scheduler")
    
    # Simular carga de configuración
    logger.info(f"Cargando {len(SCHEDULED_TASKS)} tareas programadas")
    for task in SCHEDULED_TASKS:
        logger.info(f"Tarea programada: {task['name']} - {task['schedule']} - {task['description']}")
    
    logger.info("Beat scheduler iniciado")
    
    # Simulación de ejecución continua
    while True:
        current_time = datetime.now()
        
        # Simular verificación de tareas a ejecutar
        for task in SCHEDULED_TASKS:
            # Simulamos aleatoriamente si una tarea debe ejecutarse
            if random.random() < 0.1:  # 10% de probabilidad de ejecutar cada tarea en cada ciclo
                logger.info(f"Programando tarea: {task['name']} - {task['description']}")
                
                # Simular envío a la cola
                logger.info(f"Enviando tarea {task['task']} a la cola con args: {task['args']}")
        
        # Esperar antes de la siguiente verificación
        time.sleep(60)  # Verificar cada minuto

if __name__ == "__main__":
    try:
        run_beat()
    except KeyboardInterrupt:
        logger.info("Beat scheduler detenido por el usuario")
    except Exception as e:
        logger.error(f"Error en beat scheduler: {e}")
