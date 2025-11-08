from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List
from datetime import datetime
from uuid import UUID
import re


# Auth Schemas
class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    display_name: str = Field(..., min_length=2, max_length=100)
    
    @field_validator('password')
    def validate_password(cls, v):
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'[0-9]', v):
            raise ValueError('Password must contain at least one digit')
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordReset(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)
    
    @field_validator('new_password')
    def validate_password(cls, v):
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'[0-9]', v):
            raise ValueError('Password must contain at least one digit')
        return v


# User Schemas
class UserBase(BaseModel):
    display_name: str
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    location: Optional[dict] = None
    instruments: Optional[List[str]] = None
    genres: Optional[List[str]] = None
    social_links: Optional[dict] = None


class UserUpdate(BaseModel):
    display_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    location: Optional[dict] = None
    instruments: Optional[List[str]] = None
    genres: Optional[List[str]] = None
    social_links: Optional[dict] = None


class UserPublic(BaseModel):
    id: UUID
    email: str
    display_name: str
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    location: Optional[dict] = None
    instruments: Optional[List[str]] = None
    genres: Optional[List[str]] = None
    social_links: Optional[dict] = None
    created_at: datetime
    
    model_config = {"from_attributes": True}


class UserMe(UserPublic):
    email_verified: bool
    role: str


# Band Schemas
class BandCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = None
    location: Optional[dict] = None
    genres: Optional[List[str]] = None
    avatar_url: Optional[str] = None


class BandUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    description: Optional[str] = None
    location: Optional[dict] = None
    genres: Optional[List[str]] = None
    avatar_url: Optional[str] = None


class BandResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    owner_id: UUID
    location: Optional[dict] = None
    genres: Optional[List[str]] = None
    avatar_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class BandMemberRole(BaseModel):
    role: str = Field(..., pattern="^(member|manager|owner)$")


# Post Schemas
class PostCreate(BaseModel):
    title: Optional[str] = Field(None, max_length=300)
    content: str = Field(..., min_length=1)
    media_urls: Optional[List[str]] = None
    visibility: str = Field(default="public", pattern="^(public|followers|private)$")
    band_id: Optional[UUID] = None
    parent_id: Optional[UUID] = None


class PostUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=300)
    content: Optional[str] = Field(None, min_length=1)
    media_urls: Optional[List[str]] = None
    visibility: Optional[str] = Field(None, pattern="^(public|followers|private)$")


class PostResponse(BaseModel):
    id: UUID
    author_id: UUID
    band_id: Optional[UUID] = None
    title: Optional[str] = None
    content: str
    media_urls: Optional[List[str]] = None
    visibility: str
    parent_id: Optional[UUID] = None
    is_flagged: bool
    reports: int
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


# Comment Schemas
class CommentCreate(BaseModel):
    content: str = Field(..., min_length=1)
    parent_id: Optional[UUID] = None


class CommentResponse(BaseModel):
    id: UUID
    post_id: UUID
    author_id: UUID
    content: str
    parent_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


# Message Schemas
class MessageThreadCreate(BaseModel):
    participant_ids: List[UUID] = Field(..., min_length=2)


class MessageThreadResponse(BaseModel):
    id: UUID
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1)
    attachments: Optional[List[str]] = None


class MessageResponse(BaseModel):
    id: UUID
    thread_id: UUID
    sender_id: UUID
    content: str
    attachments: Optional[List[str]] = None
    read_by: Optional[List[str]] = None
    created_at: datetime
    
    model_config = {"from_attributes": True}


# Upload Schema
class UploadResponse(BaseModel):
    url: str
    filename: str
