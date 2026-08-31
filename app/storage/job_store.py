import json
from azure.core.exceptions import ResourceNotFoundError

from app.models.resume_job import ResumeJob
from app.storage.blob_stub import BlobStorageService

blob_service = BlobStorageService()


def job_blob_path(resume_id: str) -> str:
    return f"jobs/{resume_id}/job.json"


def save_job(job: ResumeJob) -> None:
    blob_service.upload_file(
        job_blob_path(job.resume_id),
        job.model_dump_json(indent=2).encode("utf-8"),
    )


def load_job(resume_id: str) -> ResumeJob | None:
    try:
        data = blob_service.download_file(job_blob_path(resume_id))
    except ResourceNotFoundError:
        return None

    if not data:
        return None

    return ResumeJob.model_validate_json(data.decode("utf-8"))
