from typing import Dict, Set, List
from fastapi import WebSocket
import json
import logging
import redis.asyncio as aioredis
import os

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


class ConnectionManager:
    def __init__(self):
        # Map of user_id -> set of websockets
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # Redis pub/sub for multi-instance support
        self.redis: aioredis.Redis = None
        self.pubsub = None
    
    async def initialize(self):
        """Initialize Redis connection for pub/sub"""
        try:
            self.redis = await aioredis.from_url(REDIS_URL, decode_responses=True)
            self.pubsub = self.redis.pubsub()
            await self.pubsub.subscribe("messages")
            logger.info("WebSocket manager initialized with Redis pub/sub")
        except Exception as e:
            logger.error(f"Failed to initialize Redis for WebSocket: {e}")
    
    async def connect(self, websocket: WebSocket, user_id: str):
        """Connect a new WebSocket for a user"""
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)
        logger.info(f"User {user_id} connected. Total connections: {len(self.active_connections[user_id])}")
    
    def disconnect(self, websocket: WebSocket, user_id: str):
        """Disconnect a WebSocket for a user"""
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
            logger.info(f"User {user_id} disconnected")
    
    async def send_personal_message(self, message: dict, user_id: str):
        """Send message to a specific user's connections"""
        if user_id in self.active_connections:
            disconnected = set()
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending to {user_id}: {e}")
                    disconnected.add(connection)
            
            # Clean up disconnected websockets
            for conn in disconnected:
                self.disconnect(conn, user_id)
    
    async def broadcast_to_thread(self, message: dict, participant_ids: List[str]):
        """Broadcast message to all participants in a thread"""
        for user_id in participant_ids:
            await self.send_personal_message(message, user_id)
    
    async def publish_message(self, message: dict):
        """Publish message to Redis for multi-instance support"""
        if self.redis:
            try:
                await self.redis.publish("messages", json.dumps(message))
            except Exception as e:
                logger.error(f"Error publishing to Redis: {e}")
    
    async def handle_redis_messages(self):
        """Listen to Redis pub/sub and forward messages to local connections"""
        if not self.pubsub:
            return
        
        try:
            async for message in self.pubsub.listen():
                if message["type"] == "message":
                    data = json.loads(message["data"])
                    user_ids = data.get("user_ids", [])
                    for user_id in user_ids:
                        await self.send_personal_message(data, user_id)
        except Exception as e:
            logger.error(f"Error in Redis message handler: {e}")


manager = ConnectionManager()
