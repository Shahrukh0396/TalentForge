from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException, Depends
from uuid import uuid4
import json
from pydantic import BaseModel
from typing import List
from datetime import datetime
from sqlalchemy.orm import Session
from app.auth import current_user
from app.db import get_db
from app.models.resume_job import ResumeJob, ResumeHistoryItem
from app.models.resume_grant import ResumeGrant
from app.storage.blob_stub import BlobStorageService
from app.services.access import (
    grant_owner,
    grants_for_user,
    list_shares,
    require_access,
    require_owner,
    revoke_share,
    share_resume,
)
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


class ShareBody(BaseModel):
    email: str


class ShareOut(BaseModel):
    id: int
    email: str | None
    created_at: datetime


def _history(job: ResumeJob, role: str) -> ResumeHistoryItem:
    return ResumeHistoryItem(**job.model_dump(), role=role)


def _owned_job(db: Session, user: dict, resume_id: str) -> ResumeJob:
    require_owner(db, user, resume_id)
    job = get_resume_job(resume_id)
    if not job:
        raise HTTPException(status_code=404, detail="Resume not found")
    return job


def _visible_job(db: Session, user: dict, resume_id: str) -> tuple[ResumeJob, ResumeGrant]:
    grant = require_access(db, user, resume_id)
    job = get_resume_job(resume_id)
    if not job:
        raise HTTPException(status_code=404, detail="Resume not found")
    return job, grant


@router.get("", response_model=List[ResumeHistoryItem])
def list_resumes(
    user: dict = Depends(current_user),
    db: Session = Depends(get_db),
):
    items: list[ResumeHistoryItem] = []
    for grant in grants_for_user(db, user):
        job = get_resume_job(grant.resume_id)
        if job:
            items.append(_history(job, grant.role))
    return items


@router.post("", response_model=ResumeHistoryItem, status_code=201)
async def upload_resume(
    file: UploadFile = File(...),
    user: dict = Depends(current_user),
    db: Session = Depends(get_db),
):
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
    grant_owner(db, user, job.resume_id)
    return _history(job, "owner")

@router.post("/batch", response_model=List[ResumeHistoryItem], status_code=201)
async def upload_resumes(
    files: List[UploadFile] = File(...),
    user: dict = Depends(current_user),
    db: Session = Depends(get_db),
):
    if not files:
        raise HTTPException(status_code=400, detail="No files were provided")

    jobs: list[ResumeHistoryItem] = []
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
        grant_owner(db, user, job.resume_id)
        jobs.append(_history(job, "owner"))
    return jobs


@router.post("/batch/process", response_model=List[ResumeHistoryItem], status_code=202)
async def process_batch_resumes(
    payload: ResumeIdBatch,
    background_tasks: BackgroundTasks,
    user: dict = Depends(current_user),
    db: Session = Depends(get_db),
):
    for resume_id in payload.resume_ids:
        _owned_job(db, user, resume_id)

    jobs: list[ResumeHistoryItem] = []
    for resume_id in payload.resume_ids:
        try:
            jobs.append(_history(start_processing(resume_id, background_tasks), "owner"))
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Could not process resume_id={resume_id}: {exc}",
            ) from exc
    return jobs


@router.post("/{resume_id}/process", response_model=ResumeHistoryItem, status_code=202)
async def process_resume(
    resume_id: str,
    background_tasks: BackgroundTasks,
    user: dict = Depends(current_user),
    db: Session = Depends(get_db),
):
    _owned_job(db, user, resume_id)
    try:
        job = start_processing(resume_id, background_tasks)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _history(job, "owner")


@router.post("/{resume_id}/share", response_model=ShareOut, status_code=201)
def create_share(
    resume_id: str,
    payload: ShareBody,
    user: dict = Depends(current_user),
    db: Session = Depends(get_db),
):
    grant = share_resume(db, user, resume_id, payload.email)
    return ShareOut(id=grant.id, email=grant.email, created_at=grant.created_at)


@router.get("/{resume_id}/shares", response_model=List[ShareOut])
def get_shares(
    resume_id: str,
    user: dict = Depends(current_user),
    db: Session = Depends(get_db),
):
    return [
        ShareOut(id=grant.id, email=grant.email, created_at=grant.created_at)
        for grant in list_shares(db, user, resume_id)
    ]


@router.delete("/{resume_id}/shares/{share_id}", status_code=204)
def delete_share(
    resume_id: str,
    share_id: int,
    user: dict = Depends(current_user),
    db: Session = Depends(get_db),
):
    revoke_share(db, user, resume_id, share_id)


@router.get("/{resume_id}", response_model=ResumeHistoryItem)
async def get_status(
    resume_id: str,
    user: dict = Depends(current_user),
    db: Session = Depends(get_db),
):
    job, grant = _visible_job(db, user, resume_id)
    return _history(job, grant.role)


@router.get("/{resume_id}/parsed")
async def get_parsed_resume(
    resume_id: str,
    user: dict = Depends(current_user),
    db: Session = Depends(get_db),
):
    job, _grant = _visible_job(db, user, resume_id)

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
def get_docx(
    resume_id: str,
    user: dict = Depends(current_user),
    db: Session = Depends(get_db),
):
    job, _grant = _visible_job(db, user, resume_id)

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
def get_pdf(
    resume_id: str,
    user: dict = Depends(current_user),
    db: Session = Depends(get_db),
):
    job, _grant = _visible_job(db, user, resume_id)

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
