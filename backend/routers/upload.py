from fastapi import APIRouter, UploadFile, File, Form
from typing import List
import uuid
from schemas.requests import UploadRequestMetadata
from schemas.responses import TriageInitiatedResponse

router = APIRouter()

@router.post("/", response_model=TriageInitiatedResponse)
async def upload_files(
    files: List[UploadFile] = File(...),):
    triage_id = str(uuid.uuid4())
    filenames = [file.filename for file in files]