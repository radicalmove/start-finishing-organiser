from __future__ import annotations

from datetime import datetime, date, time
from enum import Enum

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .db import Base


class ProjectStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class ProjectCategory(str, Enum):
    WORK = "work"
    PERSONAL = "personal"


class ProjectSize(str, Enum):
    LIGHT = "light"
    MODERATE = "moderate"
    HEAVY = "heavy"


class SuccessLevel(str, Enum):
    SMALL = "small"
    MODERATE = "moderate"
    EPIC = "epic"


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    CANCELLED = "cancelled"


class WhenBucket(str, Enum):
    TODAY = "today"
    WEEK = "week"
    MONTH = "month"
    LATER = "later"


class BlockType(str, Enum):
    FOCUS = "focus"
    ADMIN = "admin"
    SOCIAL = "social"
    RECOVERY = "recovery"


class Alignment(str, Enum):
    ALIGNED = "aligned"
    PARTIAL = "partial"
    UNALIGNED = "unaligned"


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(160), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(SAEnum(ProjectCategory), nullable=False, default=ProjectCategory.WORK)
    status = Column(SAEnum(ProjectStatus), nullable=False, default=ProjectStatus.ACTIVE)
    size = Column(SAEnum(ProjectSize), nullable=True)
    time_horizon = Column(String(32), nullable=True)  # week/month/quarter/year
    start_date = Column(Date, nullable=True)
    target_date = Column(Date, nullable=True)
    level_of_success = Column(SAEnum(SuccessLevel), nullable=True)
    why_link_text = Column(Text, nullable=True)
    drag_points_notes = Column(Text, nullable=True)
    active_this_week = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")
    success_pack = relationship(
        "SuccessPack", back_populates="project", uselist=False, cascade="all, delete-orphan"
    )
    waiting_on = relationship(
        "WaitingOn", back_populates="project", cascade="all, delete-orphan"
    )
    blocks = relationship("Block", back_populates="project", cascade="all, delete-orphan")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    verb_noun = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    when_bucket = Column(SAEnum(WhenBucket), nullable=False, default=WhenBucket.LATER)
    block_type = Column(SAEnum(BlockType), nullable=True)
    priority = Column(Integer, nullable=True)
    frog = Column(Boolean, nullable=False, default=False)
    alignment = Column(SAEnum(Alignment), nullable=True)
    first_action = Column(String(255), nullable=True)
    status = Column(SAEnum(TaskStatus), nullable=False, default=TaskStatus.PENDING)
    scheduled_for = Column(Date, nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    project = relationship("Project", back_populates="tasks")


class Block(Base):
    __tablename__ = "blocks"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=True)
    end_time = Column(Time, nullable=True)
    block_type = Column(SAEnum(BlockType), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    project = relationship("Project", back_populates="blocks")
    task = relationship("Task")


class SuccessPack(Base):
    __tablename__ = "success_packs"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, unique=True)
    guides = Column(Text, nullable=True)
    peers = Column(Text, nullable=True)
    supporters = Column(Text, nullable=True)
    beneficiaries = Column(Text, nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    project = relationship("Project", back_populates="success_pack")


class WaitingOn(Base):
    __tablename__ = "waiting_on"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    description = Column(Text, nullable=False)
    person = Column(String(120), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_followup = Column(Date, nullable=True)

    project = relationship("Project", back_populates="waiting_on")
