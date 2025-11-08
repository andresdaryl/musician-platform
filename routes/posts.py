from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc
from database import get_db
from models import Post, Comment, Like, User, Follow, Band, TargetTypeEnum
from schemas import PostCreate, PostUpdate, PostResponse, CommentCreate, CommentResponse
from dependencies import get_current_user, get_optional_current_user, get_current_moderator
from typing import List, Optional

router = APIRouter(prefix="/posts", tags=["Posts"])


@router.post("/", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
async def create_post(
    post_data: PostCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # If band_id provided, verify user has permission
    if post_data.band_id:
        result = await db.execute(select(Band).where(Band.id == post_data.band_id))
        band = result.scalar_one_or_none()
        if not band:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Band not found"
            )
    
    # Create post
    new_post = Post(
        author_id=current_user.id,
        band_id=post_data.band_id,
        title=post_data.title,
        content=post_data.content,
        media_urls=post_data.media_urls or [],
        visibility=post_data.visibility,
        parent_id=post_data.parent_id
    )
    
    db.add(new_post)
    await db.commit()
    await db.refresh(new_post)
    
    return new_post


@router.get("/", response_model=List[PostResponse])
async def get_posts_feed(
    author_id: Optional[str] = Query(None, description="Filter by author"),
    band_id: Optional[str] = Query(None, description="Filter by band"),
    following: bool = Query(False, description="Show only posts from followed users"),
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    query = select(Post).where(Post.parent_id == None)  # Only top-level posts
    
    # Apply filters
    if author_id:
        query = query.where(Post.author_id == author_id)
    
    if band_id:
        query = query.where(Post.band_id == band_id)
    
    if following and current_user:
        # Get followed users
        followed_query = select(Follow.following_id).where(Follow.follower_id == current_user.id)
        followed_result = await db.execute(followed_query)
        followed_ids = [row[0] for row in followed_result.all()]
        
        if followed_ids:
            query = query.where(Post.author_id.in_(followed_ids))
        else:
            # No followed users, return empty
            return []
    
    # Visibility filter
    if current_user:
        # Show public, followers (if following author), and own private posts
        query = query.where(
            or_(
                Post.visibility == "public",
                Post.author_id == current_user.id
            )
        )
    else:
        # Only public posts for unauthenticated users
        query = query.where(Post.visibility == "public")
    
    query = query.order_by(desc(Post.created_at)).offset(offset).limit(limit)
    result = await db.execute(query)
    posts = result.scalars().all()
    
    return posts


@router.get("/{post_id}", response_model=PostResponse)
async def get_post(
    post_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    
    # Check visibility
    if post.visibility == "private" and (not current_user or post.author_id != current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this post"
        )
    
    if post.visibility == "followers" and current_user:
        if post.author_id != current_user.id:
            # Check if following
            result = await db.execute(
                select(Follow).where(
                    and_(
                        Follow.follower_id == current_user.id,
                        Follow.following_id == post.author_id
                    )
                )
            )
            if not result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to view this post"
                )
    
    return post


@router.patch("/{post_id}", response_model=PostResponse)
async def update_post(
    post_id: str,
    post_update: PostUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    
    # Only author or moderator can update
    if post.author_id != current_user.id and current_user.role.value not in ["moderator", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this post"
        )
    
    # Update fields
    update_data = post_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(post, field, value)
    
    await db.commit()
    await db.refresh(post)
    
    return post


@router.delete("/{post_id}")
async def delete_post(
    post_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    
    # Only author or moderator can delete
    if post.author_id != current_user.id and current_user.role.value not in ["moderator", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this post"
        )
    
    await db.delete(post)
    await db.commit()
    
    return {"message": "Post deleted successfully"}


@router.post("/{post_id}/comments", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
async def create_comment(
    post_id: str,
    comment_data: CommentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Check if post exists
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    
    # Create comment
    new_comment = Comment(
        post_id=post_id,
        author_id=current_user.id,
        content=comment_data.content,
        parent_id=comment_data.parent_id
    )
    
    db.add(new_comment)
    await db.commit()
    await db.refresh(new_comment)
    
    return new_comment


@router.get("/{post_id}/comments", response_model=List[CommentResponse])
async def get_post_comments(
    post_id: str,
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    query = (
        select(Comment)
        .where(Comment.post_id == post_id)
        .order_by(Comment.created_at)
        .offset(offset)
        .limit(limit)
    )
    
    result = await db.execute(query)
    comments = result.scalars().all()
    
    return comments


@router.post("/{post_id}/like")
async def like_post(
    post_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Check if post exists
    result = await db.execute(select(Post).where(Post.id == post_id))
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    
    # Check if already liked
    result = await db.execute(
        select(Like).where(
            and_(
                Like.target_type == TargetTypeEnum.POST,
                Like.target_id == post_id,
                Like.user_id == current_user.id
            )
        )
    )
    existing_like = result.scalar_one_or_none()
    
    if existing_like:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already liked this post"
        )
    
    # Create like
    new_like = Like(
        target_type=TargetTypeEnum.POST,
        target_id=post_id,
        user_id=current_user.id
    )
    
    db.add(new_like)
    await db.commit()
    
    return {"message": "Post liked successfully"}


@router.delete("/{post_id}/like")
async def unlike_post(
    post_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Like).where(
            and_(
                Like.target_type == TargetTypeEnum.POST,
                Like.target_id == post_id,
                Like.user_id == current_user.id
            )
        )
    )
    like = result.scalar_one_or_none()
    
    if not like:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Like not found"
        )
    
    await db.delete(like)
    await db.commit()
    
    return {"message": "Post unliked successfully"}


@router.post("/{post_id}/report")
async def report_post(
    post_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Report a post for moderation"""
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    
    # Increment report count
    post.reports += 1
    if post.reports >= 5:  # Auto-flag after 5 reports
        post.is_flagged = True
    
    await db.commit()
    
    return {"message": "Post reported successfully"}
