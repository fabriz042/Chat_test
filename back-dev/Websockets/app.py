# app.py
# Servidor WebSocket para sistema de comunicación policial en tiempo real
import asyncio
import json
import logging
import os
import datetime
import websockets
import redis
import aiohttp

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("websocket_server")

# Conexión a Redis
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
DJANGO_API_URL = os.getenv("DJANGO_API_URL", "http://localhost:8000/api")

# Clientes conectados
connected_clients = {}
active_channels = {
    "emergency": set(),
    "operations": set(),
    "admin": set(),
    "general": set(),
}

async def redis_subscriber():
    """Suscriptor de Redis para recibir mensajes de otros servicios"""
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)
        pubsub = r.pubsub()
        pubsub.subscribe("police_notifications", "emergency_alerts")
        
        logger.info("Redis subscriber iniciado")
        
        for message in pubsub.listen():
            if message["type"] == "message":
                data = json.loads(message["data"])
                channel = data.get("channel", "general")
                
                if channel in active_channels:
                    # Enviar a todos los clientes en ese canal
                    for client in active_channels[channel]:
                        await client.send(json.dumps(data))
                    
                    logger.info(f"Mensaje de Redis distribuido a {len(active_channels[channel])} clientes en canal {channel}")
    except Exception as e:
        logger.error(f"Error en Redis subscriber: {e}")
        await asyncio.sleep(5)  # Esperar antes de reintentar
        asyncio.create_task(redis_subscriber())

async def fetch_from_api(endpoint):
    """Obtener datos desde la API de Django"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{DJANGO_API_URL}/{endpoint}") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Error al obtener datos de la API: {response.status}")
                    return None
    except Exception as e:
        logger.error(f"Error al conectar con la API: {e}")
        return None

async def chat_handler(websocket, path):
    """Manejador principal de WebSocket"""
    client_id = None
    client_channel = "general"
    
    try:
        # Registro inicial y autenticación
        auth_message = await websocket.recv()
        auth_data = json.loads(auth_message)
        client_id = auth_data.get("client_id", str(id(websocket)))
        client_name = auth_data.get("name", f"Usuario-{client_id[-4:]}")
        client_role = auth_data.get("role", "officer")
        client_channel = auth_data.get("channel", "general")
        
        # Registrar cliente
        connected_clients[client_id] = {
            "websocket": websocket,
            "name": client_name,
            "role": client_role,
            "connected_at": datetime.datetime.now().isoformat(),
            "channel": client_channel
        }
        
        # Añadir al canal
        if client_channel in active_channels:
            active_channels[client_channel].add(websocket)
        
        # Enviar confirmación
        await websocket.send(json.dumps({
            "type": "system",
            "action": "connected",
            "client_id": client_id,
            "channel": client_channel,
            "timestamp": datetime.datetime.now().isoformat(),
            "message": f"Bienvenido al sistema de comunicación, {client_name}"
        }))
        
        logger.info(f"Cliente {client_name} ({client_id}) conectado al canal {client_channel}")
        
        # Notificar a otros en el mismo canal
        for client in active_channels[client_channel]:
            if client != websocket:
                await client.send(json.dumps({
                    "type": "system",
                    "action": "user_joined",
                    "client_id": client_id,
                    "name": client_name,
                    "channel": client_channel,
                    "timestamp": datetime.datetime.now().isoformat()
                }))
        
        # Procesar mensajes
        async for message in websocket:
            data = json.loads(message)
            msg_type = data.get("type", "message")
            
            # Añadir metadata
            data.update({
                "client_id": client_id,
                "name": client_name,
                "timestamp": datetime.datetime.now().isoformat(),
                "channel": client_channel
            })
            
            # Distribuir mensaje según tipo
            if msg_type == "message":
                # Mensaje normal al canal
                for client in active_channels[client_channel]:
                    await client.send(json.dumps(data))
                    
            elif msg_type == "emergency":
                # Alerta de emergencia a todos los canales
                for channel, clients in active_channels.items():
                    for client in clients:
                        await client.send(json.dumps(data))
                
            elif msg_type == "command":
                # Comando especial
                command = data.get("command")
                if command == "switch_channel":
                    new_channel = data.get("params", {}).get("channel", "general")
                    if new_channel in active_channels:
                        # Remover del canal actual
                        active_channels[client_channel].remove(websocket)
                        
                        # Notificar salida
                        for client in active_channels[client_channel]:
                            await client.send(json.dumps({
                                "type": "system",
                                "action": "user_left",
                                "client_id": client_id,
                                "name": client_name,
                                "channel": client_channel,
                                "timestamp": datetime.datetime.now().isoformat()
                            }))
                        
                        # Añadir al nuevo canal
                        client_channel = new_channel
                        connected_clients[client_id]["channel"] = client_channel
                        active_channels[client_channel].add(websocket)
                        
                        # Notificar al cliente
                        await websocket.send(json.dumps({
                            "type": "system",
                            "action": "channel_switched",
                            "channel": client_channel,
                            "timestamp": datetime.datetime.now().isoformat()
                        }))
                        
                        # Notificar a otros en el nuevo canal
                        for client in active_channels[client_channel]:
                            if client != websocket:
                                await client.send(json.dumps({
                                    "type": "system",
                                    "action": "user_joined",
                                    "client_id": client_id,
                                    "name": client_name,
                                    "channel": client_channel,
                                    "timestamp": datetime.datetime.now().isoformat()
                                }))
            
            logger.info(f"Mensaje de {client_name} en canal {client_channel}: {msg_type}")
            
    except websockets.exceptions.ConnectionClosedError:
        logger.info(f"Conexión cerrada con cliente {client_id}")
    except Exception as e:
        logger.error(f"Error en chat_handler: {e}")
    finally:
        # Limpiar al desconectar
        if client_id and client_id in connected_clients:
            del connected_clients[client_id]
        
        if client_channel in active_channels and websocket in active_channels[client_channel]:
            active_channels[client_channel].remove(websocket)
            
            # Notificar a otros en el mismo canal
            for client in active_channels[client_channel]:
                await client.send(json.dumps({
                    "type": "system",
                    "action": "user_left",
                    "client_id": client_id,
                    "channel": client_channel,
                    "timestamp": datetime.datetime.now().isoformat()
                }))
            
        logger.info(f"Cliente {client_id} desconectado del canal {client_channel}")

async def main():
    """Función principal"""
    # Iniciar suscriptor de Redis
    asyncio.create_task(redis_subscriber())
    
    # Iniciar servidor WebSocket
    server = await websockets.serve(chat_handler, "0.0.0.0", 8765)
    logger.info("Servidor WebSocket iniciado en ws://0.0.0.0:8765")
    
    # Mantener el servidor ejecutándose
    await server.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())
