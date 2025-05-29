# routers/upload.py
import uuid
from typing import List, Tuple
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Form, BackgroundTasks, HTTPException, status, Depends
from sqlalchemy.orm import Session

from services.file_manager import file_manager
from services.triage_orchestrator import triage_orchestrator
from schemas.requests import UploadRequestMetadata
from schemas.responses import TriageInitiatedResponse
from config.settings import settings
from db.database import get_db # To get DB session
from db.crud import create_triage_result, create_uploaded_file


router = APIRouter()

# Define the router for file upload operations
# returns a TriageInitiatedResponse with the triage_id and a message
@router.post("/upload", response_model=TriageInitiatedResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_files(
    background_tasks: BackgroundTasks, # Background task to handle triage processing
    files: List[UploadFile] = File(..., description="List of files to upload"), # List of files to upload
    db: Session = Depends(get_db), # Dependency to get the database session
    metadata_json: str = Form( # Optional JSON string containing metadata
        '{}',
        description="Optional JSON string containing metadata like patient_identifier, etc."
    )
):
    """
    Upload files to Supabase Storage and initiate the triage process.
    """
    try: # Validate and parse the metadata JSON string
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
    uploaded_filenames = [] # List to store filenames for database entry

    # Create a new triage result in the database
    await create_triage_result(db, triage_id, metadata.patient_identifier)

    uploaded_file_info = []

    for file in files:
        # Generate a unique filename
        if file.size is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File '{file.filename}' is empty"
            )
        if file.size > settings.MAX_FILE_SIZE_MB * 1024 * 1024:  # Convert MB to bytes, ensure the file size is within limits
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File '{file.filename}' exceeds the maximum size of {settings.MAX_FILE_SIZE} MB"
            )
        if file.content_type not in ["application/pdf", "image/jpeg", "image/png"]: # Check if the file type is allowed
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type '{file.content_type}' is not allowed. Allowed types are: {settings.ALLOWED_FILE_TYPES}"
            )

        uploaded_filenames.append(file.filename)  # Store the original filename for database entry

    uploaded_file_info: List[Tuple[str, str]] = [] # To store (storage_path, public_url) after upload

    # Upload the file to Supabase
    try:
        uploaded_file_info = await file_manager.upload_files(files, triage_id) 
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload files: {e}"
        )
    
    # Create database records for uploaded files
    for storage_path, public_url in uploaded_file_info:
        # Reconstruct original filename from storage_path for DB consistency
        original_filename = Path(storage_path).name 
        
        # Determine file_type based on suffix (ensure consistent with DocumentAnalyzer)
        file_ext = original_filename.lower().split('.')[-1]
        file_type = "document" if file_ext == "pdf" else \
                    "image" if file_ext in ["jpg", "jpeg", "png"] else \
                    "other"

        await create_uploaded_file(
            db,
            triage_id=triage_id,
            filename=storage_path,  # Use the storage path as the filename in the DB
            original_filename=original_filename,
            filepath=storage_path,  # Store the path in the DB
            file_type=file_type,
            public_url=public_url
        )

    # Start the triage process in the background
    background_tasks.add_task(
        triage_orchestrator.start_triage_process,
        db,
        triage_id,
        uploaded_file_info,
        metadata.patient_identifier
    )
    return TriageInitiatedResponse( # Response model for the upload endpoint
        triage_id=triage_id,
        message="Files uploaded successfully. Triage process has been initiated.",
        status_url=f"/status/{triage_id}",
        uploaded_filenames=[file.filename for file in files]
    )

# Note: The `triage_orchestrator` is assumed to be an instance of a class that handles the triage process.
# Ensure that the `triage_orchestrator` is properly initialized in your application startup.
# This might involve importing it from the appropriate module where it's defined.
# Ensure that the router is included in your FastAPI application


