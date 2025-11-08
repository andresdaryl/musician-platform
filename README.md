# Musician Platform API

Open-source community platform backend for musicians (Phase 1: Core Foundation)

## Features (Phase 1)

### Authentication & Authorization
- Email/password registration with verification
- JWT access + refresh tokens
- Google OAuth (placeholder)
- Password reset flow
- Role-based permissions (user, moderator, admin)
- Token revocation and logout
- Rate-limited auth endpoints

### Core Data Models
- **Users**: profiles, instruments, genres, social links
- **Bands**: band management, members with roles
- **Posts**: feed with visibility controls, media support
- **Comments**: nested comments on posts
- **Likes**: like posts and comments
- **Follow**: follow/unfollow users
- **Direct Messaging**: threads and messages with real-time support

### Real-time Features
- WebSocket messaging
- Typing indicators
- Read receipts
- Online presence
- Redis pub/sub for horizontal scaling

### Security & Validation
- Input validation with Pydantic
- Rate limiting (slowapi)
- Content moderation hooks
- Password strength enforcement
- Secure token generation

### Media Storage
- S3-compatible storage (MinIO)
- File upload with validation
- Support for images, audio, video

### Background Jobs
- Celery for async tasks
- Email sending (verification, reset)
- Media processing hooks

## Tech Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL with async SQLAlchemy
- **Cache/Pub-Sub**: Redis
- **Storage**: MinIO (S3-compatible)
- **Task Queue**: Celery
- **Migrations**: Alembic
- **Auth**: JWT with python-jose
- **WebSocket**: Native FastAPI WebSocket

## Setup Instructions

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- PostgreSQL (via Docker)
- Redis (via Docker)
- MinIO (via Docker)

### Local Development Setup

1. **Clone and navigate to backend directory**
```bash
cd /app/backend
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Start infrastructure services (Postgres, Redis, MinIO)**
```bash
cd /app
docker-compose up -d
```

This will start:
- PostgreSQL on port 5432
- Redis on port 6379
- MinIO on ports 9000 (API) and 9001 (Console)

4. **Environment variables**

The `.env` file is already configured. Key variables:
```
DATABASE_URL=postgresql+asyncpg://musicplatform:devpassword123@localhost:5432/musician_platform
REDIS_URL=redis://localhost:6379/0
JWT_SECRET_KEY=your-super-secret-jwt-key-change-in-production
MINIO_ENDPOINT=localhost:9000
```

5. **Run database migrations**
```bash
alembic upgrade head
```

6. **Seed database with sample data (optional)**
```bash
python seed_data.py
```

7. **Start Celery worker (in separate terminal)**
```bash
celery -A celery_app worker --loglevel=info
```

8. **Start FastAPI server**
```bash
python server.py
```

Or with uvicorn:
```bash
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

### Access Points

- **API**: http://localhost:8001
- **OpenAPI Docs**: http://localhost:8001/docs
- **ReDoc**: http://localhost:8001/redoc
- **MinIO Console**: http://localhost:9001 (minioadmin / minioadmin123)

## Database Migrations

### Create a new migration
```bash
alembic revision --autogenerate -m "description"
```

### Apply migrations
```bash
alembic upgrade head
```

### Rollback migrations
```bash
alembic downgrade -1
```

## API Testing

### Sample curl commands

**Register a user:**
```bash
curl -X POST http://localhost:8001/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "Password123",
    "display_name": "Test User"
  }'
```

**Login:**
```bash
curl -X POST http://localhost:8001/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "Password123"
  }'
```

**Get current user (requires token):**
```bash
curl -X GET http://localhost:8001/api/v1/users/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Create a post:**
```bash
curl -X POST http://localhost:8001/api/v1/posts \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "My first post!",
    "visibility": "public"
  }'
```

**WebSocket connection (messages):**
```javascript
const ws = new WebSocket('ws://localhost:8001/ws/messages?token=YOUR_ACCESS_TOKEN');

ws.onopen = () => {
  console.log('Connected');
  
  // Send a message
  ws.send(JSON.stringify({
    type: 'message',
    thread_id: 'THREAD_ID',
    content: 'Hello!'
  }));
};

ws.onmessage = (event) => {
  console.log('Received:', JSON.parse(event.data));
};
```

## Testing

### Run tests
```bash
pytest tests/
```

### Run with coverage
```bash
pytest --cov=. tests/
```

## Project Structure

```
backend/
├── alembic/              # Database migrations
├── routes/               # API route handlers
│   ├── auth.py          # Authentication endpoints
│   ├── users.py         # User management
│   ├── bands.py         # Band management
│   ├── posts.py         # Posts, comments, likes
│   ├── messages.py      # Direct messaging REST API
│   ├── uploads.py       # File upload
│   └── websocket.py     # WebSocket endpoint
├── models.py            # SQLAlchemy models
├── schemas.py           # Pydantic schemas
├── database.py          # Database connection
├── security.py          # Auth utilities
├── dependencies.py      # FastAPI dependencies
├── email_service.py     # Email sending
├── storage_service.py   # MinIO/S3 storage
├── websocket_manager.py # WebSocket connection manager
├── rate_limiter.py      # Rate limiting
├── celery_app.py        # Celery configuration
├── celery_tasks.py      # Background tasks
├── server.py            # Main FastAPI app
├── seed_data.py         # Database seeding script
├── requirements.txt     # Python dependencies
└── .env                 # Environment variables
```

## Sample Login Credentials

After running seed script:
```
Email: john.guitarist@example.com
Password: Password123

Email: sarah.drummer@example.com
Password: Password123
```

## Notes

- This implements **Phase 1 only**: Core social foundation
- Marketplace, lessons, payments features are NOT included
- Google OAuth is placeholder implementation
- Email service uses console logging in development
- Production deployment requires additional security hardening

## Future Phases (Not Implemented)

- Phase 2: Marketplace (instruments, equipment, services)
- Phase 3: Lessons & Booking
- Phase 4: Payments Integration
- Phase 5: Ratings & Reviews

## License

MIT License - Open Source
