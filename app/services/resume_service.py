
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
import os
import json
from app.models.resume_job import ResumeJob
from app.storage.blob_stub import BlobStorageService
from app.parsing.parser import parse_resume
from app.services.formatter_service import build_formatted_resume_docx
from app.services.openai_service import format_resume_with_openai


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

    background_tasks.add_task(process_resume_task, resume_id)

    return job

def process_resume_task(resume_id: str):
    """
    This will later:
     - parse resume
     - call Azure OpenAI
     - generate DOCX
     - upload to blob
    """

    try:
        job = RESUME_STORE[resume_id]
        
        blob_path = job.raw_blob_path
        print("Attempting to download blob:", blob_path)
        
        # Assuming `blob_service` is a global object or you have already initialized it somewhere else in your code
        raw_bytes = blob_service.download_file(blob_path)  

        if not raw_bytes:  # Ensure the file was downloaded successfully
            raise ValueError("File could not be downloaded")
        
        clean_text = parse_resume(
            file_name=blob_path.split("/")[-1],
            data=raw_bytes
        )

        structured_resume = format_resume_with_openai(clean_text)
        json_blob_path = (
            f"processed/{resume_id}/"
            f"{job.filename.rsplit('.', 1)[0]}.json"
        )
        blob_service.upload_file(
            json_blob_path,
            json.dumps(structured_resume, indent=2).encode("utf-8")
        )

        guideline_path = os.getenv("RESUME_GUIDELINES_PATH")
        letterhead_path = os.getenv("RESUME_LETTERHEAD_PATH")
        output_bytes = build_formatted_resume_docx(
            parsed_text=clean_text,
            candidate_filename=job.filename,
            guideline_path=guideline_path,
            letterhead_path=letterhead_path,
        )
        output_name = f"{job.filename.rsplit('.', 1)[0]}_parsed.docx"
        generated_blob_path = f"formatted/{resume_id}/{output_name}"
        blob_service.upload_file(generated_blob_path, output_bytes)

        job.status = "COMPLETED"
        job.completed_at = datetime.utcnow()
        job.generated_blob_path = generated_blob_path
        if blob_service.container is None:
            job.download_url = f"/api/v1/resumes/{resume_id}/download"
        else:
            job.download_url = blob_service.generate_read_url(generated_blob_path)
    
    except ValueError as e:  # File not found or could not be downloaded
        job.status = "FAILED"
        job.error_message = str(e)
        
    except Exception as e:  # Other exceptions that we didn't anticipate
        job.status = "FAILED"
        job.error_message = f"Unexpected error occurred: {str(e)}"


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