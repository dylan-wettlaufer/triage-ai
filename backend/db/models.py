# db/models.py
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from db.database import Base

class TriageResult(Base):
    __tablename__ = "triage_results"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4())) # unique id for triage result
    patient_identifier = Column(String, nullable=True) # identifier for the patient, e.g., MRN, SSN, etc.
    status = Column(String, default="pending") # e.g., pending, processing_ocr, processing_img, completed, failed
    urgency_level = Column(String, nullable=True) # e.g., low, medium, high
    diagnostic_suggestions = Column(JSON, nullable=True) # JSONB for flexible suggestions
    extracted_document_data = Column(JSON, nullable=True) # JSONB for extracted text/fields
    image_analysis_results = Column(JSON, nullable=True) # JSONB for image classifications
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    uploaded_files = relationship("UploadedFile", back_populates="triage_result")

class UploadedFile(Base):
    __tablename__ = "uploaded_files"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4())) # unique id for the uploaded file
    filename = Column(String, nullable=False) # The unique filename used in Supabase
    original_filename = Column(String, nullable=False)
    filepath = Column(String, nullable=False) # The path/key within the Supabase bucket
    triage_id = Column(String, ForeignKey("triage_results.id"), nullable=False)
    upload_time = Column(DateTime, default=datetime.utcnow)
    file_type = Column(String) # e.g., 'document', 'image'
    public_url = Column(String, nullable=True) # Public URL if bucket is public, or for signed URLs

    triage_result = relationship("TriageResult", back_populates="uploaded_files")