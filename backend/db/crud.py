from sqlalchemy.orm import Session
from db.models import TriageResult, UploadedFile
import uuid
from typing import List, Tuple

async def create_triage_result(db: Session, triage_id: str, patient_identifier: str = None) -> TriageResult:
    """
    Create a new TriageResult entry in the database.    
    """
    triage_result = TriageResult(
        id=triage_id,
        patient_identifier=patient_identifier,
        status="pending",  # Initial status
    )
    db.add(triage_result)
    db.commit()
    db.refresh(triage_result)
    return triage_result

async def get_triage_result(db: Session, triage_id: str) -> TriageResult:
    """
    Retrieve a TriageResult entry by its ID.
    """
    return db.query(TriageResult).filter(TriageResult.id == triage_id).first()

async def update_triage_result(db: Session, triage_id: str, status: str, urgency_level: str = None,
                                diagnostic_suggestions: dict = None, extracted_document_data: dict = None,
                                image_analysis_results: dict = None) -> TriageResult:
    """ 
    Update the status and other fields of a TriageResult entry.
    """
    db_triage = db.query(TriageResult).filter(TriageResult.id == triage_id).first()
    if db_triage:
        if status: db_triage.status = status
        if urgency_level: db_triage.urgency_level = urgency_level
        if diagnostic_suggestions: db_triage.diagnostic_suggestions = diagnostic_suggestions
        if extracted_document_data: db_triage.extracted_document_data = extracted_document_data
        if image_analysis_results: db_triage.image_analysis_results = image_analysis_results
        db.commit()
        db.refresh(db_triage)
    return db_triage

async def create_uploaded_file(db: Session, triage_id: str, filename: str, original_filename: str,
                                filepath: str, file_type: str, public_url: str = None) -> UploadedFile:
    """
    Create a new UploadedFile entry in the database.    
    """
    db_file = UploadedFile(id=str(uuid.uuid4()), filename=filename, original_filename=original_filename, 
                            filepath=filepath, triage_id=triage_id, file_type=file_type, public_url=public_url)
    db.add(db_file)
    db.commit()
    db.refresh(db_file)
    return db_file



