# routers/upload.py
import uuid
from typing import List
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Form, BackgroundTasks, HTTPException, status, Depends
from sqlalchemy.orm import Session

from services.file_manager import file_manager
from services.triage_orchestrator import triage_orchestrator
from schemas.requests import UploadRequestMetadata
from schemas.responses import TriageInitiatedResponse
from config.settings import settings
from db.database import get_db # To get DB session
from db.crud import create_triage_result, create_uploaded_file_record


router = APIRouter()

@router.post("/upload", response_model=TriageInitiatedResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_files(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(..., description="List of files to upload"),
    db: Session = Depends(get_db),
    metadata_json: str = Form(
        '{}',
        description="Optional JSON string containing metadata like patient_identifier, etc."
    )
):
    """
    Upload files to Supabase Storage and initiate the triage process.
    """
    try:
        metadata = UploadRequestMetadata.model_validate_json(metadata_json)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid metadata format: {e}"
        )
    
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files provided for upload."
        )
    
    # Generate a unique triage ID
    triage_id = str(uuid.uuid4())
    

