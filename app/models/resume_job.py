# app/models/resume_job.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class ResumeJob(BaseModel):
    resume_id: str
    filename: str
    status: str
    submitted_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    raw_blob_path: Optional[str] = None
    generated_blob_path: Optional[str] = None
    download_url: Optional[str] = None
    error_message: Optional[str] = None
