from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from db.models import TriageResult, UploadedFile
import uuid
from typing import Optional
from sqlalchemy import update
from sqlalchemy.orm import selectinload

# CRUD operations for TriageResult and UploadedFile models

# Create a new triage result
async def create_triage_result(db: AsyncSession, triage_id: str, patient_identifier: Optional[str] = None) -> TriageResult:
    triage_result = TriageResult(
        id=triage_id,
        patient_identifier=patient_identifier,
        status="pending",
    )
    db.add(triage_result)
    await db.commit()
    await db.refresh(triage_result)
    return triage_result

# Retrieve a triage result by ID
async def get_triage_result(db: AsyncSession, triage_id: str) -> Optional[TriageResult]:
    result = await db.execute(
        select(TriageResult)
        .options(selectinload(TriageResult.uploaded_files))
        .where(TriageResult.id == triage_id)
    )
    return result.scalars().first()

# Update an existing triage result
async def update_triage_result(
    db: AsyncSession,
    triage_id: str,
    status: Optional[str] = None,
    urgency_level: Optional[str] = None,
    diagnostic_suggestions: Optional[dict] = None,
    extracted_document_data: Optional[dict] = None,
    image_analysis_results: Optional[dict] = None
) -> Optional[TriageResult]:

    result = await db.execute(select(TriageResult).where(TriageResult.id == triage_id))
    db_triage = result.scalars().first()

    # If the triage result does not exist, return None
    if db_triage is None:
        return None
    
    # Update the fields if they are provided
    if db_triage:
        if status is not None: db_triage.status = status
        if urgency_level is not None: db_triage.urgency_level = urgency_level
        if diagnostic_suggestions is not None: db_triage.diagnostic_suggestions = diagnostic_suggestions
        if extracted_document_data is not None: db_triage.extracted_document_data = extracted_document_data
        if image_analysis_results is not None: db_triage.image_analysis_results = image_analysis_results

        await db.commit()
        await db.refresh(db_triage)

    return db_triage

# Create a new uploaded file entry
async def create_uploaded_file(
    db: AsyncSession,
    triage_id: str,
    filename: str,
    original_filename: str,
    filepath: str,
    file_type: str,
    public_url: Optional[str] = None
) -> UploadedFile:

    db_file = UploadedFile(
        id=str(uuid.uuid4()),
        filename=filename,
        original_filename=original_filename,
        filepath=filepath,
        triage_id=triage_id,
        file_type=file_type,
        public_url=public_url
    )
    db.add(db_file)
    await db.commit()
    await db.refresh(db_file)
    return db_file
