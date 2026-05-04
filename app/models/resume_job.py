from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Literal


class ResumeJob(BaseModel):
    resume_id: str
    filename: str

    status: Literal["UPLOADED", "PROCESSING", "COMPLETED", "FAILED"]

    submitted_at: datetime
    processing_started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    raw_blob_path: Optional[str] = None
    parsed_json_blob_path: Optional[str] = None
    generated_docx_blob_path: Optional[str] = None

    download_url: Optional[str] = None
    error_message: Optional[str] = None

    class Config:
        extra = "forbid"
