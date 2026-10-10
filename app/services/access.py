from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.resume_grant import ResumeGrant


def _email(user: dict) -> str:
    value = user.get("preferred_username") or ""
    return value.strip().lower() if isinstance(value, str) else ""


def _not_found() -> HTTPException:
    return HTTPException(status_code=404, detail="Resume not found")


def grant_owner(db: Session, user: dict, resume_id: str) -> ResumeGrant:
    existing = (
        db.query(ResumeGrant)
        .filter(
            ResumeGrant.resume_id == resume_id,
            ResumeGrant.tid == user["tid"],
            ResumeGrant.oid == user["oid"],
            ResumeGrant.role == "owner",
        )
        .one_or_none()
    )
    if existing:
        return existing

    grant = ResumeGrant(
        resume_id=resume_id,
        tid=user["tid"],
        oid=user["oid"],
        email=_email(user) or None,
        role="owner",
        created_at=datetime.now(timezone.utc),
    )
    db.add(grant)
    db.commit()
    db.refresh(grant)
    return grant


def _claim_email_grant(db: Session, grant: ResumeGrant, user: dict) -> ResumeGrant:
    if grant.oid:
        return grant
    grant.oid = user["oid"]
    db.commit()
    db.refresh(grant)
    return grant


def find_grant(db: Session, user: dict, resume_id: str) -> ResumeGrant | None:
    by_oid = (
        db.query(ResumeGrant)
        .filter(
            ResumeGrant.resume_id == resume_id,
            ResumeGrant.tid == user["tid"],
            ResumeGrant.oid == user["oid"],
        )
        .one_or_none()
    )
    if by_oid:
        return by_oid

    email = _email(user)
    if not email:
        return None

    by_email = (
        db.query(ResumeGrant)
        .filter(
            ResumeGrant.resume_id == resume_id,
            ResumeGrant.tid == user["tid"],
            ResumeGrant.email == email,
        )
        .one_or_none()
    )
    if by_email:
        return _claim_email_grant(db, by_email, user)
    return None


def require_access(db: Session, user: dict, resume_id: str) -> ResumeGrant:
    grant = find_grant(db, user, resume_id)
    if not grant:
        raise _not_found()
    return grant


def require_owner(db: Session, user: dict, resume_id: str) -> ResumeGrant:
    grant = require_access(db, user, resume_id)
    if grant.role != "owner":
        raise _not_found()
    return grant


def grants_for_user(db: Session, user: dict) -> list[ResumeGrant]:
    email = _email(user)
    filters = [ResumeGrant.oid == user["oid"]]
    if email:
        filters.append(ResumeGrant.email == email)
    rows = (
        db.query(ResumeGrant)
        .filter(ResumeGrant.tid == user["tid"], or_(*filters))
        .order_by(ResumeGrant.created_at.desc())
        .all()
    )

    chosen: dict[str, ResumeGrant] = {}
    for row in rows:
        current = chosen.get(row.resume_id)
        if current is None or (row.role == "owner" and current.role != "owner"):
            chosen[row.resume_id] = row
        if row.email == email and not row.oid:
            _claim_email_grant(db, row, user)
    return list(chosen.values())


def share_resume(db: Session, user: dict, resume_id: str, email: str) -> ResumeGrant:
    require_owner(db, user, resume_id)
    normalized = email.strip().lower()
    if "@" not in normalized or normalized.startswith("@") or normalized.endswith("@"):
        raise HTTPException(status_code=400, detail="Enter a work email address")
    if normalized == _email(user):
        raise HTTPException(status_code=400, detail="You already own this resume")

    existing = (
        db.query(ResumeGrant)
        .filter(
            ResumeGrant.resume_id == resume_id,
            ResumeGrant.tid == user["tid"],
            ResumeGrant.email == normalized,
        )
        .one_or_none()
    )
    if existing:
        return existing

    grant = ResumeGrant(
        resume_id=resume_id,
        tid=user["tid"],
        oid=None,
        email=normalized,
        role="viewer",
        created_at=datetime.now(timezone.utc),
    )
    db.add(grant)
    db.commit()
    db.refresh(grant)
    return grant


def list_shares(db: Session, user: dict, resume_id: str) -> list[ResumeGrant]:
    require_owner(db, user, resume_id)
    return (
        db.query(ResumeGrant)
        .filter(
            ResumeGrant.resume_id == resume_id,
            ResumeGrant.tid == user["tid"],
            ResumeGrant.role == "viewer",
        )
        .order_by(ResumeGrant.created_at.asc())
        .all()
    )


def revoke_share(db: Session, user: dict, resume_id: str, share_id: int) -> None:
    require_owner(db, user, resume_id)
    grant = (
        db.query(ResumeGrant)
        .filter(
            ResumeGrant.id == share_id,
            ResumeGrant.resume_id == resume_id,
            ResumeGrant.role == "viewer",
        )
        .one_or_none()
    )
    if not grant:
        raise _not_found()
    db.delete(grant)
    db.commit()
