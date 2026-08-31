from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ResumeJob(BaseModel):
    resume_id: str
    filename: str
    status: str

    submitted_at: datetime
    processing_started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    raw_blob_path: str
    parsed_json_blob_path: Optional[str] = None

    generated_docx_blob_path: Optional[str] = None
    generated_pdf_blob_path: Optional[str] = None   # ✅ ADD THIS

    docx_download_url: Optional[str] = None
    pdf_download_url: Optional[str] = None

    error_message: Optional[str] = None

    class Config:
        extra = "forbid"
