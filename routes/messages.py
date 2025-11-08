from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc
from database import get_db
from models import DirectMessageThread, DirectMessage, User, thread_participants
from schemas import MessageThreadCreate, MessageThreadResponse, MessageCreate, MessageResponse
from dependencies import get_current_user
from typing import List

router = APIRouter(prefix="/messages", tags=["Messages"])


@router.post("/threads", response_model=MessageThreadResponse, status_code=status.HTTP_201_CREATED)
async def create_thread(
    thread_data: MessageThreadCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Ensure current user is in participants
    participant_ids_set = set([str(pid) for pid in thread_data.participant_ids])
    participant_ids_set.add(str(current_user.id))
    
    # Verify all participants exist
    result = await db.execute(
        select(User).where(User.id.in_(participant_ids_set))
    )
    found_users = result.scalars().all()
    
    if len(found_users) != len(participant_ids_set):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or more participants not found"
        )
    
    # Check if thread already exists for these participants (for 2-person threads)
    if len(participant_ids_set) == 2:
        # Find existing thread with same participants
        subquery = (
            select(thread_participants.c.thread_id)
            .where(thread_participants.c.user_id.in_(participant_ids_set))
            .group_by(thread_participants.c.thread_id)
            .having(func.count(thread_participants.c.user_id) == 2)
        )
        
        result = await db.execute(
            select(DirectMessageThread).where(DirectMessageThread.id.in_(subquery))
        )
        existing_thread = result.scalar_one_or_none()
        
        if existing_thread:
            return existing_thread
    
    # Create new thread
    new_thread = DirectMessageThread()
    db.add(new_thread)
    await db.flush()
    
    # Add participants
    for participant_id in participant_ids_set:
        stmt = thread_participants.insert().values(
            thread_id=new_thread.id,
            user_id=participant_id
        )
        await db.execute(stmt)
    
    await db.commit()
    await db.refresh(new_thread)
    
    return new_thread


@router.get("/threads", response_model=List[MessageThreadResponse])
async def get_user_threads(
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Get threads where user is a participant
    query = (
        select(DirectMessageThread)
        .join(thread_participants, DirectMessageThread.id == thread_participants.c.thread_id)
        .where(thread_participants.c.user_id == current_user.id)
        .order_by(desc(DirectMessageThread.updated_at))
        .offset(offset)
        .limit(limit)
    )
    
    result = await db.execute(query)
    threads = result.scalars().all()
    
    return threads


@router.get("/threads/{thread_id}/messages", response_model=List[MessageResponse])
async def get_thread_messages(
    thread_id: str,
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Verify user is participant
    result = await db.execute(
        select(thread_participants).where(
            and_(
                thread_participants.c.thread_id == thread_id,
                thread_participants.c.user_id == current_user.id
            )
        )
    )
    
    if not result.first():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a participant in this thread"
        )
    
    # Get messages
    query = (
        select(DirectMessage)
        .where(DirectMessage.thread_id == thread_id)
        .order_by(DirectMessage.created_at)
        .offset(offset)
        .limit(limit)
    )
    
    result = await db.execute(query)
    messages = result.scalars().all()
    
    return messages


@router.post("/threads/{thread_id}/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def send_message(
    thread_id: str,
    message_data: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Verify user is participant
    result = await db.execute(
        select(thread_participants).where(
            and_(
                thread_participants.c.thread_id == thread_id,
                thread_participants.c.user_id == current_user.id
            )
        )
    )
    
    if not result.first():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a participant in this thread"
        )
    
    # Create message
    new_message = DirectMessage(
        thread_id=thread_id,
        sender_id=current_user.id,
        content=message_data.content,
        attachments=message_data.attachments or [],
        read_by=[str(current_user.id)]  # Sender has read it
    )
    
    db.add(new_message)
    
    # Update thread's updated_at
    result = await db.execute(select(DirectMessageThread).where(DirectMessageThread.id == thread_id))
    thread = result.scalar_one_or_none()
    if thread:
        from datetime import datetime, timezone
        thread.updated_at = datetime.now(timezone.utc)
    
    await db.commit()
    await db.refresh(new_message)
    
    # TODO: Broadcast via WebSocket to other participants
    # This will be handled in the WebSocket endpoint
    
    return new_message


@router.post("/threads/{thread_id}/messages/{message_id}/read")
async def mark_message_read(
    thread_id: str,
    message_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Verify user is participant
    result = await db.execute(
        select(thread_participants).where(
            and_(
                thread_participants.c.thread_id == thread_id,
                thread_participants.c.user_id == current_user.id
            )
        )
    )
    
    if not result.first():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a participant in this thread"
        )
    
    # Get message
    result = await db.execute(
        select(DirectMessage).where(
            and_(
                DirectMessage.id == message_id,
                DirectMessage.thread_id == thread_id
            )
        )
    )
    message = result.scalar_one_or_none()
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )
    
    # Add user to read_by if not already
    read_by_list = message.read_by or []
    user_id_str = str(current_user.id)
    
    if user_id_str not in read_by_list:
        read_by_list.append(user_id_str)
        message.read_by = read_by_list
        await db.commit()
    
    return {"message": "Message marked as read"}
