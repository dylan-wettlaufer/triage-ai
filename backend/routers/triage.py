# routers/triage.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from db.crud import get_triage_result
from schemas.responses import TriageInitiatedResponse # Re-use or create a new one for results

router = APIRouter()

@router.get("/{triage_id}/status")
async def get_triage_status(triage_id: str, db: AsyncSession = Depends(get_db)):
    """
    Retrieves the current status and results of a triage process.
    """
    triage_result = await get_triage_result(db, triage_id)

    if not triage_result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Triage ID not found.")

    # Convert database model to a Pydantic dict for response
    # You might want a dedicated Pydantic schema for TriageResultResponse here
    response_data = {
        "triage_id": triage_result.id,
        "status": triage_result.status,
        "urgency_level": triage_result.urgency_level,
        "diagnostic_suggestions": triage_result.diagnostic_suggestions,
        "extracted_document_data": triage_result.extracted_document_data,
        "image_analysis_results": triage_result.image_analysis_results,
        "created_at": triage_result.created_at.isoformat(),
        "updated_at": triage_result.updated_at.isoformat() if triage_result.updated_at else None,
        # Add details about uploaded files if needed
        "uploaded_files": [{"original_filename": uf.original_filename, "file_type": uf.file_type, "public_url": uf.public_url} for uf in triage_result.uploaded_files]
    }
    
    return response_data