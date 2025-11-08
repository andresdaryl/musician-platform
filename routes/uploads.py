from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from dependencies import get_current_user
from models import User
from schemas import UploadResponse
from storage_service import storage_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/uploads", tags=["Uploads"])

ALLOWED_EXTENSIONS = {
    'image': ['jpg', 'jpeg', 'png', 'gif', 'webp'],
    'audio': ['mp3', 'wav', 'ogg', 'flac'],
    'video': ['mp4', 'mov', 'avi', 'mkv']
}

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


@router.post("/", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    # Validate file extension
    filename = file.filename.lower()
    extension = filename.split('.')[-1] if '.' in filename else ''
    
    allowed = False
    for file_type, extensions in ALLOWED_EXTENSIONS.items():
        if extension in extensions:
            allowed = True
            break
    
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed types: {', '.join([ext for exts in ALLOWED_EXTENSIONS.values() for ext in exts])}"
        )
    
    # Read file content
    file_content = await file.read()
    
    # Check file size
    if len(file_content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE / (1024 * 1024)}MB"
        )
    
    try:
        # Upload to storage
        url = await storage_service.upload_file(
            file_content,
            file.filename,
            file.content_type
        )
        
        logger.info(f"File uploaded by user {current_user.id}: {url}")
        
        return UploadResponse(
            url=url,
            filename=file.filename
        )
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload file"
        )
