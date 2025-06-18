#!/usr/bin/env python3
# notification-service/app.py
# Service for handling system notifications through multiple channels (websockets, email, SMS)

import os
import json
import logging
import asyncio
import httpx
from datetime import datetime
from typing import Dict, List, Optional, Union
from pydantic import BaseModel, Field
import redis.asyncio as redis
import uvicorn
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("notification-service")

# Initialize FastAPI app
app = FastAPI(
    title="SmartPoli Notification Service",
    description="Handles notification delivery across multiple channels",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify the domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Environment variables
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")
WEBSOCKET_SERVICE_URL = os.getenv("WEBSOCKET_SERVICE_URL", "http://websocket-service:8000")
EMAIL_SERVICE_URL = os.getenv("EMAIL_SERVICE_URL", "http://email-service.shared-services:8000")
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth-service.shared-services:8000")

# Initialize Redis pool
async def get_redis_pool():
    return redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        password=REDIS_PASSWORD,
        decode_responses=True,
    )

# Models
class NotificationBase(BaseModel):
    title: str
    message: str
    priority: str = Field(default="normal", description="Priority level: low, normal, high, critical")
    data: Optional[Dict] = Field(default=None, description="Additional notification data")

class UserNotification(NotificationBase):
    user_id: str
    channels: List[str] = Field(default=["websocket"], description="Notification channels: websocket, email, sms")

class BroadcastNotification(NotificationBase):
    roles: List[str] = Field(default=["all"], description="Roles to broadcast to: all, officer, supervisor, admin")
    channels: List[str] = Field(default=["websocket"], description="Notification channels: websocket, email, sms")

class NotificationStatus(BaseModel):
    notification_id: str
    status: str
    channels: Dict[str, str]
    created_at: str
    delivered_at: Optional[str] = None

# Health check dependency
async def check_services_health():
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            redis_conn = await get_redis_pool()
            await redis_conn.ping()
            
            # Check other essential services if needed
            return True
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return False

# Endpoints
@app.get("/", include_in_schema=False)
async def root():
    return {"message": "SmartPoli Notification Service"}

@app.get("/health", status_code=200)
async def health_check():
    is_healthy = await check_services_health()
    if not is_healthy:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "unhealthy"}
        )
    return {"status": "healthy"}

@app.get("/api/v1/notifications/status/{notification_id}")
async def get_notification_status(
    notification_id: str,
    redis_conn: redis.Redis = Depends(get_redis_pool)
):
    """Get the status of a specific notification"""
    try:
        notification_data = await redis_conn.get(f"notification:{notification_id}")
        if not notification_data:
            raise HTTPException(status_code=404, detail="Notification not found")
        
        notification = json.loads(notification_data)
        return notification
    except Exception as e:
        logger.error(f"Error retrieving notification status: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve notification status")

@app.post("/api/v1/notifications/user", status_code=status.HTTP_202_ACCEPTED)
async def send_user_notification(
    notification: UserNotification,
    background_tasks: BackgroundTasks,
    redis_conn: redis.Redis = Depends(get_redis_pool)
):
    """Send a notification to a specific user"""
    try:
        notification_id = f"user-{notification.user_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Store notification in Redis
        notification_data = {
            "notification_id": notification_id,
            "type": "user",
            "content": notification.dict(),
            "status": "pending",
            "channels": {channel: "pending" for channel in notification.channels},
            "created_at": datetime.now().isoformat(),
        }
        
        await redis_conn.set(
            f"notification:{notification_id}", 
            json.dumps(notification_data),
            ex=86400  # Expire after 24 hours
        )
        
        # Add to processing queue
        background_tasks.add_task(process_notification, notification_data)
        
        return {"notification_id": notification_id, "status": "accepted"}
    except Exception as e:
        logger.error(f"Error creating user notification: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create notification")

@app.post("/api/v1/notifications/broadcast", status_code=status.HTTP_202_ACCEPTED)
async def send_broadcast_notification(
    notification: BroadcastNotification,
    background_tasks: BackgroundTasks,
    redis_conn: redis.Redis = Depends(get_redis_pool)
):
    """Broadcast a notification to users with specific roles"""
    try:
        notification_id = f"broadcast-{'-'.join(notification.roles)}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Store notification in Redis
        notification_data = {
            "notification_id": notification_id,
            "type": "broadcast",
            "content": notification.dict(),
            "status": "pending",
            "channels": {channel: "pending" for channel in notification.channels},
            "created_at": datetime.now().isoformat(),
        }
        
        await redis_conn.set(
            f"notification:{notification_id}", 
            json.dumps(notification_data),
            ex=86400  # Expire after 24 hours
        )
        
        # Add to processing queue
        background_tasks.add_task(process_notification, notification_data)
        
        return {"notification_id": notification_id, "status": "accepted"}
    except Exception as e:
        logger.error(f"Error creating broadcast notification: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create notification")

@app.get("/api/v1/notifications/user/{user_id}")
async def get_user_notifications(
    user_id: str,
    limit: int = 50,
    redis_conn: redis.Redis = Depends(get_redis_pool)
):
    """Get recent notifications for a specific user"""
    try:
        # In a real implementation, this would query a database
        # For this demo, we'll search through Redis keys
        user_notifications = []
        cursor = 0
        pattern = f"notification:user-{user_id}-*"
        
        while True:
            cursor, keys = await redis_conn.scan(cursor=cursor, match=pattern, count=100)
            
            for key in keys:
                notification_data = await redis_conn.get(key)
                if notification_data:
                    user_notifications.append(json.loads(notification_data))
            
            if cursor == 0 or len(user_notifications) >= limit:
                break
                
        return {"notifications": user_notifications[:limit]}
    except Exception as e:
        logger.error(f"Error retrieving user notifications: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve notifications")

# Background processing functions
async def process_notification(notification_data: Dict):
    """Process a notification and send it through specified channels"""
    notification_id = notification_data["notification_id"]
    channels = notification_data["content"]["channels"]
    
    try:
        redis_conn = await get_redis_pool()
        
        # Update status to processing
        notification_data["status"] = "processing"
        await redis_conn.set(
            f"notification:{notification_id}", 
            json.dumps(notification_data),
            ex=86400
        )
        
        # Process each channel
        channel_tasks = []
        
        if "websocket" in channels:
            channel_tasks.append(send_websocket_notification(notification_data))
            
        if "email" in channels:
            channel_tasks.append(send_email_notification(notification_data))
            
        if "sms" in channels:
            channel_tasks.append(send_sms_notification(notification_data))
        
        # Wait for all channel tasks to complete
        results = await asyncio.gather(*channel_tasks, return_exceptions=True)
        
        # Update channel statuses
        for i, channel in enumerate(channels):
            if isinstance(results[i], Exception):
                notification_data["channels"][channel] = "failed"
                logger.error(f"Failed to send notification via {channel}: {str(results[i])}")
            else:
                notification_data["channels"][channel] = "delivered"
        
        # Check if all channels were processed
        if all(status == "delivered" for status in notification_data["channels"].values()):
            notification_data["status"] = "delivered"
            notification_data["delivered_at"] = datetime.now().isoformat()
        elif any(status == "failed" for status in notification_data["channels"].values()):
            notification_data["status"] = "partially_delivered"
        
        # Update notification in Redis
        await redis_conn.set(
            f"notification:{notification_id}", 
            json.dumps(notification_data),
            ex=86400
        )
        
    except Exception as e:
        logger.error(f"Error processing notification {notification_id}: {str(e)}")
        try:
            # Try to update the status to failed
            notification_data["status"] = "failed"
            await redis_conn.set(
                f"notification:{notification_id}", 
                json.dumps(notification_data),
                ex=86400
            )
        except:
            pass

async def send_websocket_notification(notification_data: Dict):
    """Send notification through websocket service"""
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            if notification_data["type"] == "user":
                user_id = notification_data["content"]["user_id"]
                response = await client.post(
                    f"{WEBSOCKET_SERVICE_URL}/api/v1/send/user/{user_id}",
                    json={
                        "event": "notification",
                        "data": {
                            "title": notification_data["content"]["title"],
                            "message": notification_data["content"]["message"],
                            "priority": notification_data["content"]["priority"],
                            "data": notification_data["content"]["data"],
                            "timestamp": notification_data["created_at"]
                        }
                    }
                )
            else:  # broadcast
                roles = notification_data["content"]["roles"]
                response = await client.post(
                    f"{WEBSOCKET_SERVICE_URL}/api/v1/broadcast",
                    json={
                        "roles": roles,
                        "event": "notification",
                        "data": {
                            "title": notification_data["content"]["title"],
                            "message": notification_data["content"]["message"],
                            "priority": notification_data["content"]["priority"],
                            "data": notification_data["content"]["data"],
                            "timestamp": notification_data["created_at"]
                        }
                    }
                )
            
            if response.status_code != 200:
                logger.warning(f"Websocket service returned status {response.status_code}: {response.text}")
                return False
                
            return True
        except Exception as e:
            logger.error(f"Error sending websocket notification: {str(e)}")
            raise

async def send_email_notification(notification_data: Dict):
    """Send notification through email service"""
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            if notification_data["type"] == "user":
                # Get user email from auth service
                user_id = notification_data["content"]["user_id"]
                user_response = await client.get(f"{AUTH_SERVICE_URL}/api/v1/users/{user_id}")
                
                if user_response.status_code != 200:
                    logger.warning(f"Auth service returned status {user_response.status_code}")
                    return False
                
                user_data = user_response.json()
                email = user_data.get("email")
                
                if not email:
                    logger.warning(f"No email found for user {user_id}")
                    return False
                
                # Send email
                response = await client.post(
                    f"{EMAIL_SERVICE_URL}/api/v1/email/send",
                    json={
                        "to": [email],
                        "subject": notification_data["content"]["title"],
                        "template_name": "notification",
                        "template_data": {
                            "title": notification_data["content"]["title"],
                            "message": notification_data["content"]["message"],
                            "priority": notification_data["content"]["priority"],
                            "timestamp": notification_data["created_at"]
                        }
                    }
                )
            else:  # broadcast
                # Get emails for all users with the specified roles
                roles = notification_data["content"]["roles"]
                users_response = await client.post(
                    f"{AUTH_SERVICE_URL}/api/v1/users/by-roles",
                    json={"roles": roles}
                )
                
                if users_response.status_code != 200:
                    logger.warning(f"Auth service returned status {users_response.status_code}")
                    return False
                
                users_data = users_response.json()
                emails = [user.get("email") for user in users_data.get("users", []) if user.get("email")]
                
                if not emails:
                    logger.warning(f"No emails found for roles {roles}")
                    return False
                
                # Send emails (in a real system, we'd use BCC or batch send)
                response = await client.post(
                    f"{EMAIL_SERVICE_URL}/api/v1/email/send",
                    json={
                        "to": emails,
                        "subject": notification_data["content"]["title"],
                        "template_name": "notification",
                        "template_data": {
                            "title": notification_data["content"]["title"],
                            "message": notification_data["content"]["message"],
                            "priority": notification_data["content"]["priority"],
                            "timestamp": notification_data["created_at"]
                        }
                    }
                )
            
            if response.status_code not in (200, 202):
                logger.warning(f"Email service returned status {response.status_code}: {response.text}")
                return False
                
            return True
        except Exception as e:
            logger.error(f"Error sending email notification: {str(e)}")
            raise

async def send_sms_notification(notification_data: Dict):
    """
    Send notification through SMS service
    This is a mock implementation as we don't have an actual SMS service
    """
    try:
        # Simulate SMS sending delay
        await asyncio.sleep(1)
        
        # In a real implementation, this would call an SMS provider API
        logger.info(f"SMS notification would be sent: {notification_data['content']['message']}")
        
        return True
    except Exception as e:
        logger.error(f"Error sending SMS notification: {str(e)}")
        raise

# Main
if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=os.getenv("DEBUG", "False").lower() == "true"
    )
