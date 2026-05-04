
"""
resume_service.py

Central business logic for resume processing.
- Manages resume job lifecycle
- Integrates blob storage
- Runs background parsing
- Prepares for OpenAI + DOCX stages
"""

from datetime import datetime
from typing import Dict
import json
from app.models.resume_job import ResumeJob
from app.storage.blob_stub import BlobStorageService
from app.parsing.parser import parse_resume
from app.services.openai_service import format_resume_with_openai
from app.services.docx_renderer import render_resume_docx

RESUME_STORE: Dict[str, ResumeJob] = {}

blob_service = BlobStorageService()



def create_resume_job(
    resume_id: str,
    filename: str,
    raw_blob_path: str
) -> ResumeJob:
    """
    Creates a new ResumeJob after upload.
    """
    job = ResumeJob(
        resume_id=resume_id,
        filename=filename,
        status="UPLOADED",
        submitted_at=datetime.utcnow(),
        raw_blob_path=raw_blob_path
    )

    RESUME_STORE[resume_id] = job
    return job


def start_processing(resume_id: str, background_tasks) -> ResumeJob:
    """
    Transitions a resume job into PROCESSING state and
    launches the background task.
    """
    job = RESUME_STORE.get(resume_id)

    if not job:
        raise ValueError("Resume job not found")

    if job.status not in ["UPLOADED", "FAILED"]:
        raise ValueError("Resume job cannot be processed in its current state")

    job.status = "PROCESSING"
    job.processing_started_at = datetime.utcnow()
    background_tasks.add_task(process_resume_task, resume_id)

    return job


def process_resume_task(resume_id: str):
    try:
        job = RESUME_STORE.get(resume_id)
        if not job:
            raise ValueError("Resume job no longer exists")

        raw_bytes = blob_service.download_file(job.raw_blob_path)
        if not raw_bytes:
            raise ValueError("File could not be downloaded")

        clean_text = parse_resume(
            file_name=job.raw_blob_path.split("/")[-1],
            data=raw_bytes
        )

        structured_resume = format_resume_with_openai(clean_text)

        json_blob_path = f"processed/{resume_id}/resume.json"
        blob_service.upload_file(
            json_blob_path,
            json.dumps(structured_resume, indent=2).encode("utf-8")
        )

        docx_bytes = render_resume_docx(structured_resume)
        print("Generated DOCX size:", len(docx_bytes))

        generated_docx_blob_path = f"generated/{resume_id}/resume.docx"
        blob_service.upload_file(generated_docx_blob_path, docx_bytes)

        job.parsed_json_blob_path = json_blob_path
        job.generated_docx_blob_path = generated_docx_blob_path
        job.status = "COMPLETED"
        job.completed_at = datetime.utcnow()
        job.download_url = f"/api/v1/resumes/{resume_id}/download"

    except Exception as e:
        if job:
            job.status = "FAILED"
            job.error_message = str(e)



def get_resume_job(resume_id: str) -> ResumeJob | None:
    """
    Returns a resume job by ID.
    """
    return RESUME_STORE.get(resume_id)


def list_resume_jobs() -> list[ResumeJob]:
    """
    Returns all resume jobs.
    """
    return list(RESUME_STORE.values())