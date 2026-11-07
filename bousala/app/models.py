from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from pgvector.sqlalchemy import Vector
from app.config import DIM

class Base(DeclarativeBase):
    pass

class Source(Base):
    __tablename__ = 'source_documents'
    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(Text)
    path: Mapped[str] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(String)
    catalog: Mapped[str] = mapped_column(String, default='44:2024-2025')
    provenance: Mapped[str] = mapped_column(String)
    dates: Mapped[dict] = mapped_column(JSONB, default=dict)
    sha256: Mapped[str] = mapped_column(String)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

class Chunk(Base):
    __tablename__ = 'document_chunks'
    id: Mapped[str] = mapped_column(String, primary_key=True)
    source_id: Mapped[str] = mapped_column(ForeignKey('source_documents.id', ondelete='CASCADE'), index=True)
    page: Mapped[int | None] = mapped_column(Integer)
    topic: Mapped[str] = mapped_column(Text)
    text: Mapped[str] = mapped_column(Text)
    normalized: Mapped[str] = mapped_column(Text)
    token_count: Mapped[int] = mapped_column(Integer)
    chunk_hash: Mapped[str] = mapped_column(String)
    details: Mapped[dict] = mapped_column(JSONB, default=dict)
    embedding: Mapped[list] = mapped_column(Vector(DIM))
    __table_args__ = (CheckConstraint('page IS NULL OR page > 0'),)

class Course(Base):
    __tablename__ = 'courses'
    id: Mapped[str] = mapped_column(String, primary_key=True)
    catalog_id: Mapped[str] = mapped_column(String, default='44')
    code: Mapped[str] = mapped_column(String, index=True)
    name: Mapped[str] = mapped_column(Text)
    credits: Mapped[int] = mapped_column(Integer)
    category: Mapped[str] = mapped_column(String)
    applicability: Mapped[dict] = mapped_column(JSONB)
    evidence: Mapped[list] = mapped_column(JSONB)
    placeholder: Mapped[bool] = mapped_column(Boolean, default=False)
    __table_args__ = (UniqueConstraint('catalog_id', 'code'), CheckConstraint('credits BETWEEN 0 AND 4'))

class Prerequisite(Base):
    __tablename__ = 'prerequisite_rules'
    code: Mapped[str] = mapped_column(String, primary_key=True)
    operator: Mapped[str] = mapped_column(String)
    required: Mapped[list] = mapped_column(JSONB)
    provenance: Mapped[str] = mapped_column(String)
    evidence: Mapped[dict] = mapped_column(JSONB)
    caution: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (CheckConstraint("operator = 'AND'"),)

class Setting(Base):
    __tablename__ = 'index_settings'
    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[dict] = mapped_column(JSONB)

class FAQ(Base):
    __tablename__ = 'faq_seeds'
    id: Mapped[str] = mapped_column(String, primary_key=True)
    question: Mapped[str] = mapped_column(Text)
    topic: Mapped[str] = mapped_column(String)
    seed: Mapped[bool] = mapped_column(Boolean, default=True)

class Event(Base):
    __tablename__ = 'question_events'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    question_hash: Mapped[str] = mapped_column(String, index=True)
    category: Mapped[str] = mapped_column(String)
    latency_ms: Mapped[float] = mapped_column(Float)
    refusal: Mapped[bool] = mapped_column(Boolean)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class Cache(Base):
    __tablename__ = 'answer_cache'
    key: Mapped[str] = mapped_column(String, primary_key=True)
    response: Mapped[dict] = mapped_column(JSONB)

class Evaluation(Base):
    __tablename__ = 'evaluation_runs'
    id: Mapped[str] = mapped_column(String, primary_key=True)
    dataset_hash: Mapped[str] = mapped_column(String)
    results: Mapped[dict] = mapped_column(JSONB)
