
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
from app.services.pdf_service import convert_docx_to_pdf
from app.storage.blob_stub import BlobStorageService
from app.storage.job_store import load_job, save_job
from app.parsing.parser import parse_resume
from app.services.openai_service import format_resume_with_openai
from app.services.docx_renderer import render_resume_docx
from app.utils.helpers import resolve_candidate_name

RESUME_STORE: Dict[str, ResumeJob] = {}

blob_service = BlobStorageService()


def _persist_job(job: ResumeJob) -> ResumeJob:
    RESUME_STORE[job.resume_id] = job
    save_job(job)
    return job


def _generated_output_name(filename: str, extension: str) -> str:
    base = filename.rsplit(".", 1)[0]
    return f"{base}.{extension}"


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

    return _persist_job(job)


def start_processing(resume_id: str, background_tasks) -> ResumeJob:
    """
    Transitions a resume job into PROCESSING state and
    launches the background task.
    """
    job = get_resume_job(resume_id)

    if not job:
        raise ValueError("Resume job not found")

    if job.status not in ["UPLOADED", "FAILED"]:
        raise ValueError("Resume job cannot be processed in its current state")

    job.status = "PROCESSING"
    job.processing_started_at = datetime.utcnow()
    _persist_job(job)

    background_tasks.add_task(process_resume_task, resume_id)

    return job


def process_resume_task(resume_id: str):
    job = get_resume_job(resume_id)

    if not job:
        print(f"PROCESSING ERROR: resume job {resume_id} no longer exists")
        return

    try:
        job.status = "PROCESSING"
        job.processing_started_at = datetime.utcnow()
        _persist_job(job)

        raw_bytes = blob_service.download_file(job.raw_blob_path)

        if not raw_bytes:
            raise ValueError("File could not be downloaded")

        clean_text = parse_resume(
            file_name=job.raw_blob_path.split("/")[-1],
            data=raw_bytes
        )

        structured_resume = format_resume_with_openai(clean_text)
        structured_resume["name"] = resolve_candidate_name(
            structured_resume,
            clean_text,
            job.filename,
        )

        json_blob_path = f"processed/{resume_id}/resume.json"
        blob_service.upload_file(
            json_blob_path,
            json.dumps(structured_resume, indent=2).encode("utf-8")
        )

        docx_bytes = render_resume_docx(structured_resume)
        docx_name = _generated_output_name(job.filename, "docx")
        generated_docx_blob_path = f"generated/{resume_id}/{docx_name}"
        blob_service.upload_file(generated_docx_blob_path, docx_bytes)

        pdf_bytes = convert_docx_to_pdf(docx_bytes)
        pdf_name = _generated_output_name(job.filename, "pdf")
        generated_pdf_blob_path = f"generated/{resume_id}/{pdf_name}"
        blob_service.upload_file(generated_pdf_blob_path, pdf_bytes)

        job.parsed_json_blob_path = json_blob_path
        job.generated_docx_blob_path = generated_docx_blob_path
        job.generated_pdf_blob_path = generated_pdf_blob_path
        job.status = "COMPLETED"
        job.completed_at = datetime.utcnow()
        job.error_message = None
        job.docx_download_url = f"/api/v1/resumes/{resume_id}/docx"
        job.pdf_download_url = f"/api/v1/resumes/{resume_id}/pdf"

        _persist_job(job)

    except Exception as e:
        job.status = "FAILED"
        job.error_message = str(e)
        job.completed_at = datetime.utcnow()
        _persist_job(job)
        print("PROCESSING ERROR:", str(e))


def get_resume_job(resume_id: str) -> ResumeJob | None:
    """
    Returns a resume job by ID from memory cache or blob storage.
    """
    cached = RESUME_STORE.get(resume_id)
    if cached:
        return cached

    job = load_job(resume_id)
    if job:
        RESUME_STORE[resume_id] = job
    return job


def get_generated_docx_bytes(resume_id: str) -> bytes | None:
    job = get_resume_job(resume_id)
    if not job or not job.generated_docx_blob_path:
        return None
    return blob_service.download_file(job.generated_docx_blob_path)


def get_generated_pdf_bytes(resume_id: str) -> bytes | None:
    job = get_resume_job(resume_id)
    if not job or not job.generated_pdf_blob_path:
        return None
    return blob_service.download_file(job.generated_pdf_blob_path)


def list_resume_jobs() -> list[ResumeJob]:
    """
    Returns all resume jobs currently cached in memory.
    """
    return list(RESUME_STORE.values())
