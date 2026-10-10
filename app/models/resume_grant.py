from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class ResumeGrant(Base):
    __tablename__ = "resume_grants"

    id: Mapped[int] = mapped_column(primary_key=True)
    resume_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    tid: Mapped[str] = mapped_column(String(64), nullable=False)
    oid: Mapped[str | None] = mapped_column(String(64), nullable=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
