# schemas/requests.py
# This file contains request schemas for the FastAPI application.
# It defines the data structures used for incoming requests.
from pydantic import BaseModel, Field

class UploadRequestMetadata(BaseModel):
    patient_identifier: str = Field(
        default="anonymous",
        description="An identifier for the patient, can be a temporary ID."
    )