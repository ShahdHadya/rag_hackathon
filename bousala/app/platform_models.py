"""Additive platform tables. Legacy academic rows remain intact and referenced."""
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.models import Base

def uid():
    return str(uuid4())

def now():
    return datetime.now(timezone.utc)

class Program(Base):
    __tablename__='academic_programs'
    id: Mapped[str]=mapped_column(String,primary_key=True)
    name_ar: Mapped[str]=mapped_column(Text)
    name_en: Mapped[str]=mapped_column(Text)
    university: Mapped[str]=mapped_column(Text,default='Bethlehem University')
    faculty: Mapped[str|None]=mapped_column(Text)
    department: Mapped[str|None]=mapped_column(Text)
    official_code: Mapped[str|None]=mapped_column(String)
    verified: Mapped[bool]=mapped_column(Boolean,default=False)

class Curriculum(Base):
    __tablename__='curriculum_versions'
    id: Mapped[str]=mapped_column(String,primary_key=True)
    program_id: Mapped[str]=mapped_column(ForeignKey('academic_programs.id'),index=True)
    catalog_id: Mapped[str]=mapped_column(String)
    year: Mapped[str]=mapped_column(String)
    title: Mapped[str]=mapped_column(Text)
    status: Mapped[str]=mapped_column(String,default='draft')
    base_credits: Mapped[int|None]=mapped_column(Integer)
    rules: Mapped[dict]=mapped_column(JSONB,default=dict)
    revision: Mapped[int]=mapped_column(Integer,default=1)
    evidence: Mapped[list]=mapped_column(JSONB,default=list)
    __table_args__=(UniqueConstraint('program_id','catalog_id','year'),CheckConstraint("status IN ('draft','review','published','archived')"))

class RequirementGroup(Base):
    __tablename__='requirement_groups'
    id: Mapped[str]=mapped_column(String,primary_key=True)
    curriculum_id: Mapped[str]=mapped_column(ForeignKey('curriculum_versions.id'),index=True)
    name: Mapped[str]=mapped_column(Text)
    category: Mapped[str]=mapped_column(String)
    kind: Mapped[str]=mapped_column(String)  # all / elective / english
    credits: Mapped[int]=mapped_column(Integer)
    track_credits: Mapped[dict]=mapped_column(JSONB,default=dict)
    evidence: Mapped[list]=mapped_column(JSONB,default=list)

class CurriculumCourse(Base):
    __tablename__='curriculum_courses'
    id: Mapped[str]=mapped_column(String,primary_key=True)
    curriculum_id: Mapped[str]=mapped_column(ForeignKey('curriculum_versions.id'),index=True)
    course_id: Mapped[str]=mapped_column(ForeignKey('courses.id'),index=True)
    group_id: Mapped[str]=mapped_column(ForeignKey('requirement_groups.id'))
    title: Mapped[str]=mapped_column(Text)
    credits: Mapped[int]=mapped_column(Integer)
    tracks: Mapped[list]=mapped_column(JSONB,default=list)
    mandatory: Mapped[bool]=mapped_column(Boolean)
    options: Mapped[list]=mapped_column(JSONB,default=list)
    suggested: Mapped[list]=mapped_column(JSONB,default=list)
    evidence: Mapped[list]=mapped_column(JSONB,default=list)
    verified: Mapped[bool]=mapped_column(Boolean,default=False)
    __table_args__=(UniqueConstraint('curriculum_id','course_id'),CheckConstraint('credits >= 0 AND credits <= 30'))

class CurriculumPrerequisite(Base):
    __tablename__='curriculum_prerequisites'
    id: Mapped[str]=mapped_column(String,primary_key=True)
    curriculum_id: Mapped[str]=mapped_column(ForeignKey('curriculum_versions.id'),index=True)
    course_id: Mapped[str]=mapped_column(ForeignKey('courses.id'))
    expression: Mapped[dict]=mapped_column(JSONB)
    corequisite: Mapped[dict|None]=mapped_column(JSONB)
    evidence: Mapped[list]=mapped_column(JSONB)
    caution: Mapped[str|None]=mapped_column(Text)
    verified: Mapped[bool]=mapped_column(Boolean,default=False)
    __table_args__=(UniqueConstraint('curriculum_id','course_id'),)

class User(Base):
    __tablename__='users'
    id: Mapped[str]=mapped_column(String,primary_key=True,default=uid)
    email: Mapped[str]=mapped_column(String(254),unique=True,index=True)
    display_name: Mapped[str]=mapped_column(String(100))
    password_hash: Mapped[str]=mapped_column(Text)
    role: Mapped[str]=mapped_column(String,default='student')
    active: Mapped[bool]=mapped_column(Boolean,default=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
    __table_args__=(CheckConstraint("role IN ('student','admin')"),)

class AuthSession(Base):
    __tablename__='auth_sessions'
    token_hash: Mapped[str]=mapped_column(String,primary_key=True)
    user_id: Mapped[str]=mapped_column(ForeignKey('users.id',ondelete='CASCADE'),index=True)
    expires_at: Mapped[datetime]=mapped_column(DateTime(timezone=True))

class Profile(Base):
    __tablename__='student_profiles'
    user_id: Mapped[str]=mapped_column(ForeignKey('users.id'),primary_key=True)
    student_number: Mapped[str|None]=mapped_column(String(40))
    curriculum_id: Mapped[str|None]=mapped_column(ForeignKey('curriculum_versions.id'))
    english_track: Mapped[str|None]=mapped_column(String)
    self_reported: Mapped[bool]=mapped_column(Boolean,default=True)

class Attempt(Base):
    __tablename__='student_course_attempts'
    id: Mapped[str]=mapped_column(String,primary_key=True,default=uid)
    user_id: Mapped[str]=mapped_column(ForeignKey('users.id'),index=True)
    curriculum_course_id: Mapped[str]=mapped_column(ForeignKey('curriculum_courses.id'),index=True)
    status: Mapped[str]=mapped_column(String)
    grade: Mapped[str|None]=mapped_column(String)
    term: Mapped[str|None]=mapped_column(String(80))
    option_code: Mapped[str|None]=mapped_column(String)
    active: Mapped[bool]=mapped_column(Boolean,default=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
    __table_args__=(CheckConstraint("status IN ('completed','in_progress','failed','not_taken')"),)

class Plan(Base):
    __tablename__='student_academic_plans'
    id: Mapped[str]=mapped_column(String,primary_key=True,default=uid)
    user_id: Mapped[str]=mapped_column(ForeignKey('users.id'),index=True)
    curriculum_id: Mapped[str]=mapped_column(ForeignKey('curriculum_versions.id'))
    name: Mapped[str]=mapped_column(String(100))
    course_ids: Mapped[list]=mapped_column(JSONB)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)

class Conversation(Base):
    __tablename__='conversations'
    id: Mapped[str]=mapped_column(String,primary_key=True,default=uid)
    user_id: Mapped[str]=mapped_column(ForeignKey('users.id'),index=True)
    curriculum_id: Mapped[str]=mapped_column(ForeignKey('curriculum_versions.id'))
    title: Mapped[str]=mapped_column(String(120))
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)

class Message(Base):
    __tablename__='messages'
    id: Mapped[str]=mapped_column(String,primary_key=True,default=uid)
    conversation_id: Mapped[str]=mapped_column(ForeignKey('conversations.id'),index=True)
    role: Mapped[str]=mapped_column(String)
    content: Mapped[str]=mapped_column(Text)
    citations: Mapped[list]=mapped_column(JSONB,default=list)
    kind: Mapped[str|None]=mapped_column(String)
    refusal: Mapped[bool]=mapped_column(Boolean,default=False)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)

class DocumentVersion(Base):
    __tablename__='document_versions'
    id: Mapped[str]=mapped_column(String,primary_key=True,default=uid)
    source_id: Mapped[str]=mapped_column(ForeignKey('source_documents.id'),unique=True)
    family_id: Mapped[str]=mapped_column(String,index=True)
    version: Mapped[int]=mapped_column(Integer)
    uploaded_by: Mapped[str|None]=mapped_column(ForeignKey('users.id'))
    pages: Mapped[list]=mapped_column(JSONB,default=list)
    issues: Mapped[list]=mapped_column(JSONB,default=list)
    review_notes: Mapped[str|None]=mapped_column(Text)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)

class AuditLog(Base):
    __tablename__='audit_logs'
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    user_id: Mapped[str|None]=mapped_column(ForeignKey('users.id'))
    action: Mapped[str]=mapped_column(String)
    target: Mapped[str|None]=mapped_column(String)
    details: Mapped[dict]=mapped_column(JSONB,default=dict)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)

class QuestionLog(Base):
    __tablename__='question_logs'
    id: Mapped[str]=mapped_column(String,primary_key=True,default=uid)
    user_id: Mapped[str|None]=mapped_column(ForeignKey('users.id'))
    curriculum_id: Mapped[str|None]=mapped_column(ForeignKey('curriculum_versions.id'))
    category: Mapped[str]=mapped_column(String)
    question: Mapped[str]=mapped_column(Text)
    refusal: Mapped[bool]=mapped_column(Boolean)
    latency_ms: Mapped[float]=mapped_column(Float)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
