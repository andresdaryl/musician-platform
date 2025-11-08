from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func
from database import get_db
from models import User, Follow
from schemas import UserMe, UserPublic, UserUpdate
from dependencies import get_current_user, get_optional_current_user
from typing import List, Optional

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserMe)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    return current_user


@router.patch("/me", response_model=UserMe)
async def update_current_user_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Update fields
    update_data = user_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(current_user, field, value)
    
    await db.commit()
    await db.refresh(current_user)
    
    return current_user


@router.get("/{user_id}", response_model=UserPublic)
async def get_user_by_id(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user


@router.get("/", response_model=List[UserPublic])
async def search_users(
    q: Optional[str] = Query(None, description="Search query"),
    instruments: Optional[str] = Query(None, description="Comma-separated instruments"),
    genres: Optional[str] = Query(None, description="Comma-separated genres"),
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    query = select(User).where(User.is_active == True)
    
    if q:
        query = query.where(
            or_(
                User.display_name.ilike(f"%{q}%"),
                User.email.ilike(f"%{q}%")
            )
        )
    
    if instruments:
        instrument_list = [i.strip() for i in instruments.split(",")]
        query = query.where(User.instruments.overlap(instrument_list))
    
    if genres:
        genre_list = [g.strip() for g in genres.split(",")]
        query = query.where(User.genres.overlap(genre_list))
    
    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    users = result.scalars().all()
    
    return users


@router.post("/{user_id}/follow")
async def follow_user(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if str(current_user.id) == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot follow yourself"
        )
    
    # Check if target user exists
    result = await db.execute(select(User).where(User.id == user_id))
    target_user = result.scalar_one_or_none()
    
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if already following
    result = await db.execute(
        select(Follow).where(
            Follow.follower_id == current_user.id,
            Follow.following_id == user_id
        )
    )
    existing_follow = result.scalar_one_or_none()
    
    if existing_follow:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already following this user"
        )
    
    # Create follow
    follow = Follow(
        follower_id=current_user.id,
        following_id=user_id
    )
    db.add(follow)
    await db.commit()
    
    return {"message": "Successfully followed user"}


@router.delete("/{user_id}/follow")
async def unfollow_user(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Follow).where(
            Follow.follower_id == current_user.id,
            Follow.following_id == user_id
        )
    )
    follow = result.scalar_one_or_none()
    
    if not follow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not following this user"
        )
    
    await db.delete(follow)
    await db.commit()
    
    return {"message": "Successfully unfollowed user"}


@router.get("/{user_id}/followers", response_model=List[UserPublic])
async def get_user_followers(
    user_id: str,
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    query = (
        select(User)
        .join(Follow, Follow.follower_id == User.id)
        .where(Follow.following_id == user_id)
        .offset(offset)
        .limit(limit)
    )
    
    result = await db.execute(query)
    followers = result.scalars().all()
    
    return followers


@router.get("/{user_id}/following", response_model=List[UserPublic])
async def get_user_following(
    user_id: str,
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    query = (
        select(User)
        .join(Follow, Follow.following_id == User.id)
        .where(Follow.follower_id == user_id)
        .offset(offset)
        .limit(limit)
    )
    
    result = await db.execute(query)
    following = result.scalars().all()
    
    return following
