from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException, Response
from uuid import uuid4
import json
from typing import List
from app.models.resume_job import ResumeJob
from app.storage.blob_stub import BlobStorageService
from app.services.resume_service import (
    create_resume_job,
    start_processing,
    get_resume_job
)

router = APIRouter()
blob_service = BlobStorageService()

@router.post("", response_model=ResumeJob, status_code=201)
async def upload_resume(file: UploadFile = File(...)):
    resume_id = str(uuid4())
    file_bytes = await file.read()
    safe_filename = file.filename.strip()
    blob_path = f"raw/{resume_id}/{safe_filename}"
    print("Uploaded blob:", blob_path)
    blob_service.upload_file(
        blob_path,
        file_bytes
    )
    job = create_resume_job(
        resume_id=resume_id,
        filename=file.filename,
        raw_blob_path=blob_path
    )

    return job

@router.post("/batch", response_model=List[ResumeJob], status_code=201)
async def upload_resumes(files: List[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="No files were provided")

    jobs: list[ResumeJob] = []
    for file in files:
        resume_id = str(uuid4())
        file_bytes = await file.read()
        blob_path = f"raw/{resume_id}/{file.filename}"
        blob_service.upload_file(blob_path=blob_path, data=file_bytes)
        job = create_resume_job(
            resume_id=resume_id,
            filename=file.filename,
            raw_blob_path=blob_path,
        )
        jobs.append(job)
    return jobs

@router.post("/{resume_id}/process", response_model=ResumeJob, status_code=202)
async def process_resume(
    resume_id: str,
    background_tasks: BackgroundTasks
):
    try:
        job = start_processing(resume_id, background_tasks)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return job


@router.post("/batch/process", response_model=List[ResumeJob], status_code=202)
async def process_batch_resumes(
    resume_ids: List[str],
    background_tasks: BackgroundTasks,
):
    jobs: list[ResumeJob] = []
    for resume_id in resume_ids:
        try:
            jobs.append(start_processing(resume_id, background_tasks))
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Could not process resume_id={resume_id}: {exc}",
            ) from exc
    return jobs

@router.get("/{resume_id}", response_model=ResumeJob)
async def get_status(resume_id: str):
    job = get_resume_job(resume_id)
    if not job:
        raise HTTPException(status_code=404, detail="Resume not found")
    return job

@router.get("/{resume_id}/parsed")
async def get_parsed_resume(resume_id: str):
    job = get_resume_job(resume_id)

    if not job:
        raise HTTPException(status_code=404, detail="Resume not found")

    if job.status != "COMPLETED":
        raise HTTPException(status_code=400, detail="Resume not processed yet")

    parsed_blob_path = f"processed/{resume_id}/{job.filename.rsplit('.', 1)[0]}.json"

    try:
        parsed_bytes = blob_service.download_file(parsed_blob_path)
    except Exception:
        raise HTTPException(status_code=404, detail="Parsed data not found")

    return json.loads(parsed_bytes)   


@router.get("/{resume_id}/download")
async def download_result(resume_id: str):
    job = get_resume_job(resume_id)
    print("DOWNLOAD BLOB PATH:", job.raw_blob_path)
    if not job:
        raise HTTPException(status_code=404, detail="Resume not found")
    if job.status != "COMPLETED" or not job.generated_blob_path:
        raise HTTPException(status_code=400, detail="Resume is not ready for download")

    output_bytes = blob_service.download_file(job.generated_blob_path)
    if not output_bytes:
        raise HTTPException(status_code=404, detail="Generated file not found")

    output_name = f"{job.filename.rsplit('.', 1)[0]}_parsed.docx"
    return Response(
        content=output_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{output_name}"'},
    )