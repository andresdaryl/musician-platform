from sqlalchemy import Column, String, Boolean, DateTime, Text, JSON, ForeignKey, Table, Enum as SQLEnum, Index, Integer
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid
import enum
from database import Base


class RoleEnum(str, enum.Enum):
    USER = "user"
    MODERATOR = "moderator"
    ADMIN = "admin"


class VisibilityEnum(str, enum.Enum):
    PUBLIC = "public"
    FOLLOWERS = "followers"
    PRIVATE = "private"


class TargetTypeEnum(str, enum.Enum):
    POST = "post"
    COMMENT = "comment"


class BandMemberRoleEnum(str, enum.Enum):
    MEMBER = "member"
    MANAGER = "manager"
    OWNER = "owner"


# Association table for band members
band_members = Table(
    'band_members',
    Base.metadata,
    Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    Column('band_id', UUID(as_uuid=True), ForeignKey('bands.id', ondelete='CASCADE'), nullable=False),
    Column('user_id', UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
    Column('role', SQLEnum(BandMemberRoleEnum), default=BandMemberRoleEnum.MEMBER, nullable=False),
    Column('joined_at', DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)),
    Index('idx_band_members_band', 'band_id'),
    Index('idx_band_members_user', 'user_id')
)

# Association table for message thread participants
thread_participants = Table(
    'thread_participants',
    Base.metadata,
    Column('thread_id', UUID(as_uuid=True), ForeignKey('direct_message_threads.id', ondelete='CASCADE'), primary_key=True),
    Column('user_id', UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    Column('joined_at', DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)),
    Index('idx_thread_participants_thread', 'thread_id'),
    Index('idx_thread_participants_user', 'user_id')
)


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    email_verified = Column(Boolean, default=False, nullable=False)
    hashed_password = Column(String(255), nullable=True)  # Nullable for OAuth-only accounts
    display_name = Column(String(100), nullable=False)
    bio = Column(Text, nullable=True)
    avatar_url = Column(String(500), nullable=True)
    location = Column(JSON, nullable=True)  # {"city": "", "country": ""}
    instruments = Column(ARRAY(String), default=list, nullable=True)
    genres = Column(ARRAY(String), default=list, nullable=True)
    social_links = Column(JSON, nullable=True)  # {"instagram": "", "youtube": ""}
    role = Column(SQLEnum(RoleEnum), default=RoleEnum.USER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    google_id = Column(String(255), nullable=True, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    owned_bands = relationship("Band", back_populates="owner", foreign_keys="Band.owner_id")
    posts = relationship("Post", back_populates="author", foreign_keys="Post.author_id")
    comments = relationship("Comment", back_populates="author")
    sent_messages = relationship("DirectMessage", back_populates="sender")

    __table_args__ = (
        Index('idx_users_email', 'email'),
        Index('idx_users_created_at', 'created_at'),
    )


class Band(Base):
    __tablename__ = "bands"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    owner_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    location = Column(JSON, nullable=True)
    genres = Column(ARRAY(String), default=list, nullable=True)
    avatar_url = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    owner = relationship("User", back_populates="owned_bands", foreign_keys=[owner_id])
    posts = relationship("Post", back_populates="band")

    __table_args__ = (
        Index('idx_bands_owner', 'owner_id'),
        Index('idx_bands_created_at', 'created_at'),
    )


class Post(Base):
    __tablename__ = "posts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    author_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    band_id = Column(UUID(as_uuid=True), ForeignKey('bands.id', ondelete='CASCADE'), nullable=True, index=True)
    title = Column(String(300), nullable=True)
    content = Column(Text, nullable=False)
    media_urls = Column(JSON, default=list, nullable=True)  # List of URLs
    visibility = Column(SQLEnum(VisibilityEnum), default=VisibilityEnum.PUBLIC, nullable=False)
    parent_id = Column(UUID(as_uuid=True), ForeignKey('posts.id', ondelete='CASCADE'), nullable=True)  # For threading
    is_flagged = Column(Boolean, default=False, nullable=False)
    reports = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    author = relationship("User", back_populates="posts", foreign_keys=[author_id])
    band = relationship("Band", back_populates="posts")
    comments = relationship("Comment", back_populates="post", cascade="all, delete-orphan")
    replies = relationship("Post", backref="parent", remote_side=[id])

    __table_args__ = (
        Index('idx_posts_author', 'author_id'),
        Index('idx_posts_band', 'band_id'),
        Index('idx_posts_created_at', 'created_at'),
        Index('idx_posts_visibility', 'visibility'),
    )


class Comment(Base):
    __tablename__ = "comments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    post_id = Column(UUID(as_uuid=True), ForeignKey('posts.id', ondelete='CASCADE'), nullable=False, index=True)
    author_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    content = Column(Text, nullable=False)
    parent_id = Column(UUID(as_uuid=True), ForeignKey('comments.id', ondelete='CASCADE'), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    post = relationship("Post", back_populates="comments")
    author = relationship("User", back_populates="comments")
    replies = relationship("Comment", backref="parent", remote_side=[id])

    __table_args__ = (
        Index('idx_comments_post', 'post_id'),
        Index('idx_comments_author', 'author_id'),
        Index('idx_comments_created_at', 'created_at'),
    )


class Like(Base):
    __tablename__ = "likes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    target_type = Column(SQLEnum(TargetTypeEnum), nullable=False)
    target_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        Index('idx_likes_target', 'target_type', 'target_id'),
        Index('idx_likes_user', 'user_id'),
        Index('idx_likes_unique', 'target_type', 'target_id', 'user_id', unique=True),
    )


class Follow(Base):
    __tablename__ = "follows"

    follower_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), primary_key=True, index=True)
    following_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        Index('idx_follows_follower', 'follower_id'),
        Index('idx_follows_following', 'following_id'),
    )


class DirectMessageThread(Base):
    __tablename__ = "direct_message_threads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    messages = relationship("DirectMessage", back_populates="thread", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_dm_threads_created_at', 'created_at'),
    )


class DirectMessage(Base):
    __tablename__ = "direct_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    thread_id = Column(UUID(as_uuid=True), ForeignKey('direct_message_threads.id', ondelete='CASCADE'), nullable=False, index=True)
    sender_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    content = Column(Text, nullable=False)
    attachments = Column(JSON, default=list, nullable=True)
    read_by = Column(JSON, default=list, nullable=True)  # List of user IDs who read the message
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    # Relationships
    thread = relationship("DirectMessageThread", back_populates="messages")
    sender = relationship("User", back_populates="sent_messages")

    __table_args__ = (
        Index('idx_dm_thread', 'thread_id'),
        Index('idx_dm_sender', 'sender_id'),
        Index('idx_dm_created_at', 'created_at'),
    )


class EmailVerificationToken(Base):
    __tablename__ = "email_verification_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    token = Column(String(255), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    token = Column(String(255), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    token = Column(String(500), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        Index('idx_refresh_tokens_user', 'user_id'),
        Index('idx_refresh_tokens_token', 'token'),
    )
