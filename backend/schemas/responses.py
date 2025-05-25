# schemas/responses.py
# This file contains response schemas for the FastAPI application.
# It defines the data structures used for outgoing responses.
from pydantic import BaseModel
from typing import List

# schema for when the traige process is initiated
class TriageInitiatedResponse(BaseModel):
    message: str = "Files uploaded and triage processing initiated."
    triage_id: str
    uploaded_filenames: List[str]
    status_url: str