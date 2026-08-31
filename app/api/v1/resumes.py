from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException
from uuid import uuid4
import json
import base64
from pydantic import BaseModel
from typing import List, Dict, Any
from app.models.resume_job import ResumeJob
from app.storage.blob_stub import BlobStorageService
from app.services.resume_service import (
    create_resume_job,
    start_processing,
    get_resume_job,
    get_generated_docx_bytes,
    get_generated_pdf_bytes,
)
from fastapi.responses import StreamingResponse
from io import BytesIO



router = APIRouter()
blob_service = BlobStorageService()


class DownloadResponse(BaseModel):
    filename: str
    content_base64: str

class ResumeIdBatch(BaseModel):    
    resume_ids: List[str]

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
    payload: ResumeIdBatch,
    background_tasks: BackgroundTasks,
):
    jobs: list[ResumeJob] = []
    for resume_id in payload.resume_ids:
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
    return ResumeJob.model_validate(job.model_dump()).model_dump()


@router.get("/{resume_id}/parsed")
async def get_parsed_resume(resume_id: str):
    job = get_resume_job(resume_id)

    if not job:
        raise HTTPException(status_code=404, detail="Resume job not found")

    if job.status != "COMPLETED":
        raise HTTPException(
            status_code=400,
            detail="Resume not processed yet"
        )

    if not job.parsed_json_blob_path:
        raise HTTPException(
            status_code=404,
            detail="Parsed data not found"
        )

    parsed_bytes = blob_service.download_file(job.parsed_json_blob_path)

    if not parsed_bytes:
        raise HTTPException(
            status_code=404,
            detail="Parsed data not found"
        )

    return json.loads(parsed_bytes)



@router.get("/{resume_id}/docx")
def get_docx(resume_id: str):
    job = get_resume_job(resume_id)

    if not job:
        raise HTTPException(status_code=404, detail="Resume not found")

    if job.status != "COMPLETED" or not job.generated_docx_blob_path:
        raise HTTPException(status_code=400, detail="Resume not ready")

    docx_bytes = get_generated_docx_bytes(resume_id)
    if not docx_bytes:
        raise HTTPException(status_code=404, detail="Generated DOCX not found in storage")

    output_name = f"{job.filename.rsplit('.', 1)[0]}.docx"

    return StreamingResponse(
        BytesIO(docx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename={output_name}'},
    )



@router.get("/{resume_id}/pdf")
def get_pdf(resume_id: str):
    job = get_resume_job(resume_id)

    if not job:
        raise HTTPException(status_code=404, detail="Resume not found")

    if job.status != "COMPLETED" or not job.generated_pdf_blob_path:
        raise HTTPException(status_code=400, detail="Resume not ready")

    pdf_bytes = get_generated_pdf_bytes(resume_id)
    if not pdf_bytes:
        raise HTTPException(status_code=404, detail="Generated PDF not found in storage")

    output_name = f"{job.filename.rsplit('.', 1)[0]}.pdf"

    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename={output_name}'},
    )
