from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from database import get_db
from models import User, DirectMessage, thread_participants
from security import decode_token
from websocket_manager import manager
import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

router = APIRouter()


async def get_user_from_token(token: str, db: AsyncSession) -> User:
    """Authenticate user from WebSocket token"""
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        return None
    
    user_id = payload.get("sub")
    if not user_id:
        return None
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    return user if user and user.is_active else None


@router.websocket("/ws/messages")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    # Authenticate
    async for db in get_db():
        user = await get_user_from_token(token, db)
        break
    
    if not user:
        await websocket.close(code=1008, reason="Unauthorized")
        return
    
    user_id = str(user.id)
    
    # Connect
    await manager.connect(websocket, user_id)
    logger.info(f"WebSocket connected for user {user_id}")
    
    try:
        # Send connection success message
        await websocket.send_json({
            "type": "connection",
            "status": "connected",
            "user_id": user_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            message_type = message_data.get("type")
            
            if message_type == "message":
                # Handle new message
                thread_id = message_data.get("thread_id")
                content = message_data.get("content")
                
                if not thread_id or not content:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Missing thread_id or content"
                    })
                    continue
                
                # Verify user is participant and save message
                async for db in get_db():
                    result = await db.execute(
                        select(thread_participants).where(
                            and_(
                                thread_participants.c.thread_id == thread_id,
                                thread_participants.c.user_id == user.id
                            )
                        )
                    )
                    
                    if not result.first():
                        await websocket.send_json({
                            "type": "error",
                            "message": "Not a participant in this thread"
                        })
                        continue
                    
                    # Save message
                    new_message = DirectMessage(
                        thread_id=thread_id,
                        sender_id=user.id,
                        content=content,
                        attachments=message_data.get("attachments", []),
                        read_by=[user_id]
                    )
                    
                    db.add(new_message)
                    await db.commit()
                    await db.refresh(new_message)
                    
                    # Get all participants
                    result = await db.execute(
                        select(thread_participants.c.user_id).where(
                            thread_participants.c.thread_id == thread_id
                        )
                    )
                    participant_ids = [str(row[0]) for row in result.all()]
                    
                    break
                
                # Broadcast to all participants
                broadcast_message = {
                    "type": "new_message",
                    "message": {
                        "id": str(new_message.id),
                        "thread_id": thread_id,
                        "sender_id": user_id,
                        "content": content,
                        "attachments": new_message.attachments,
                        "created_at": new_message.created_at.isoformat()
                    }
                }
                
                await manager.broadcast_to_thread(broadcast_message, participant_ids)
            
            elif message_type == "typing":
                # Handle typing indicator
                thread_id = message_data.get("thread_id")
                is_typing = message_data.get("is_typing", False)
                
                if thread_id:
                    # Get participants and broadcast
                    async for db in get_db():
                        result = await db.execute(
                            select(thread_participants.c.user_id).where(
                                thread_participants.c.thread_id == thread_id
                            )
                        )
                        participant_ids = [str(row[0]) for row in result.all() if str(row[0]) != user_id]
                        break
                    
                    typing_message = {
                        "type": "typing",
                        "thread_id": thread_id,
                        "user_id": user_id,
                        "is_typing": is_typing
                    }
                    
                    await manager.broadcast_to_thread(typing_message, participant_ids)
            
            elif message_type == "read_receipt":
                # Handle read receipt
                message_id = message_data.get("message_id")
                thread_id = message_data.get("thread_id")
                
                if message_id and thread_id:
                    async for db in get_db():
                        result = await db.execute(
                            select(DirectMessage).where(
                                and_(
                                    DirectMessage.id == message_id,
                                    DirectMessage.thread_id == thread_id
                                )
                            )
                        )
                        message = result.scalar_one_or_none()
                        
                        if message:
                            read_by_list = message.read_by or []
                            if user_id not in read_by_list:
                                read_by_list.append(user_id)
                                message.read_by = read_by_list
                                await db.commit()
                            
                            # Get participants and broadcast
                            result = await db.execute(
                                select(thread_participants.c.user_id).where(
                                    thread_participants.c.thread_id == thread_id
                                )
                            )
                            participant_ids = [str(row[0]) for row in result.all()]
                        break
                    
                    receipt_message = {
                        "type": "read_receipt",
                        "message_id": message_id,
                        "thread_id": thread_id,
                        "user_id": user_id
                    }
                    
                    await manager.broadcast_to_thread(receipt_message, participant_ids)
            
            elif message_type == "ping":
                # Handle ping/pong for keeping connection alive
                await websocket.send_json({"type": "pong"})
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for user {user_id}")
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
    finally:
        manager.disconnect(websocket, user_id)
