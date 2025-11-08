from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_
from database import get_db
from models import Band, User, band_members, BandMemberRoleEnum
from schemas import BandCreate, BandUpdate, BandResponse, BandMemberRole
from dependencies import get_current_user
from typing import List, Optional

router = APIRouter(prefix="/bands", tags=["Bands"])


@router.post("/", response_model=BandResponse, status_code=status.HTTP_201_CREATED)
async def create_band(
    band_data: BandCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Create band
    new_band = Band(
        name=band_data.name,
        description=band_data.description,
        owner_id=current_user.id,
        location=band_data.location,
        genres=band_data.genres,
        avatar_url=band_data.avatar_url
    )
    
    db.add(new_band)
    await db.commit()
    await db.refresh(new_band)
    
    # Add creator as owner in band_members
    stmt = band_members.insert().values(
        band_id=new_band.id,
        user_id=current_user.id,
        role=BandMemberRoleEnum.OWNER
    )
    await db.execute(stmt)
    await db.commit()
    
    return new_band


@router.get("/{band_id}", response_model=BandResponse)
async def get_band(
    band_id: str,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Band).where(Band.id == band_id))
    band = result.scalar_one_or_none()
    
    if not band:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Band not found"
        )
    
    return band


@router.patch("/{band_id}", response_model=BandResponse)
async def update_band(
    band_id: str,
    band_update: BandUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Get band
    result = await db.execute(select(Band).where(Band.id == band_id))
    band = result.scalar_one_or_none()
    
    if not band:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Band not found"
        )
    
    # Check permissions (owner or moderator)
    if band.owner_id != current_user.id and current_user.role.value not in ["moderator", "admin"]:
        # Check if user is a manager
        result = await db.execute(
            select(band_members).where(
                and_(
                    band_members.c.band_id == band_id,
                    band_members.c.user_id == current_user.id,
                    band_members.c.role == BandMemberRoleEnum.MANAGER
                )
            )
        )
        if not result.first():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
    
    # Update fields
    update_data = band_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(band, field, value)
    
    await db.commit()
    await db.refresh(band)
    
    return band


@router.get("/", response_model=List[BandResponse])
async def search_bands(
    q: Optional[str] = Query(None, description="Search query"),
    genres: Optional[str] = Query(None, description="Comma-separated genres"),
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    query = select(Band)
    
    if q:
        query = query.where(
            or_(
                Band.name.ilike(f"%{q}%"),
                Band.description.ilike(f"%{q}%")
            )
        )
    
    if genres:
        genre_list = [g.strip() for g in genres.split(",")]
        query = query.where(Band.genres.overlap(genre_list))
    
    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    bands = result.scalars().all()
    
    return bands


@router.post("/{band_id}/apply")
async def apply_to_band(
    band_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Check if band exists
    result = await db.execute(select(Band).where(Band.id == band_id))
    band = result.scalar_one_or_none()
    
    if not band:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Band not found"
        )
    
    # For now, auto-add as member (in production, implement approval flow)
    # Check if already a member
    result = await db.execute(
        select(band_members).where(
            and_(
                band_members.c.band_id == band_id,
                band_members.c.user_id == current_user.id
            )
        )
    )
    if result.first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already a member of this band"
        )
    
    # Add as member
    stmt = band_members.insert().values(
        band_id=band_id,
        user_id=current_user.id,
        role=BandMemberRoleEnum.MEMBER
    )
    await db.execute(stmt)
    await db.commit()
    
    return {"message": "Successfully joined band"}


@router.post("/{band_id}/invite")
async def invite_to_band(
    band_id: str,
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Check if band exists and user has permission
    result = await db.execute(select(Band).where(Band.id == band_id))
    band = result.scalar_one_or_none()
    
    if not band:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Band not found"
        )
    
    # Check permissions
    if band.owner_id != current_user.id:
        result = await db.execute(
            select(band_members).where(
                and_(
                    band_members.c.band_id == band_id,
                    band_members.c.user_id == current_user.id,
                    or_(
                        band_members.c.role == BandMemberRoleEnum.MANAGER,
                        band_members.c.role == BandMemberRoleEnum.OWNER
                    )
                )
            )
        )
        if not result.first():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
    
    # Check if target user exists
    result = await db.execute(select(User).where(User.id == user_id))
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # For now, auto-add (in production, implement invitation flow)
    # Check if already a member
    result = await db.execute(
        select(band_members).where(
            and_(
                band_members.c.band_id == band_id,
                band_members.c.user_id == user_id
            )
        )
    )
    if result.first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already a member"
        )
    
    # Add as member
    stmt = band_members.insert().values(
        band_id=band_id,
        user_id=user_id,
        role=BandMemberRoleEnum.MEMBER
    )
    await db.execute(stmt)
    await db.commit()
    
    return {"message": "User invited successfully"}


@router.post("/{band_id}/members/{user_id}/role")
async def update_member_role(
    band_id: str,
    user_id: str,
    role_data: BandMemberRole,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Check if band exists
    result = await db.execute(select(Band).where(Band.id == band_id))
    band = result.scalar_one_or_none()
    
    if not band:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Band not found"
        )
    
    # Only owner can change roles
    if band.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only band owner can manage roles"
        )
    
    # Update role
    stmt = (
        band_members.update()
        .where(
            and_(
                band_members.c.band_id == band_id,
                band_members.c.user_id == user_id
            )
        )
        .values(role=role_data.role)
    )
    
    result = await db.execute(stmt)
    
    if result.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )
    
    await db.commit()
    
    return {"message": "Role updated successfully"}
