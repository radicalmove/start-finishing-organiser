#!/usr/bin/env python3
from __future__ import annotations

import argparse
import random
from datetime import date, datetime, time, timedelta

from sqlalchemy import text

from app.db import (
    Base,
    SessionLocal,
    engine,
    ensure_block_title_column,
    ensure_guidance_reminder_columns,
    ensure_project_color_column,
    ensure_ritual_columns,
    ensure_ritual_table,
    ensure_task_owner_column,
    ensure_task_resurface_columns,
)
from app.models import (
    Alignment,
    Block,
    BlockType,
    CoachConversation,
    CoachMessage,
    GuidanceEvent,
    HealthEntry,
    HealthGoal,
    HealthMetric,
    OwnerType,
    Profile,
    Project,
    ProjectCategory,
    ProjectSize,
    ProjectStatus,
    RitualEntry,
    RitualType,
    SuccessLevel,
    SuccessPack,
    Task,
    TaskStatus,
    WhenBucket,
    WaitingOn,
)
from app.utils.health import ensure_health_metrics
from app.utils.projects import PROJECT_COLOR_CHOICES


def reset_db(session) -> None:
    tables = [
        "coach_messages",
        "coach_conversations",
        "guidance_events",
        "guidance_reminders",
        "health_entries",
        "health_goals",
        "health_metrics",
        "blocks",
        "tasks",
        "waiting_on",
        "success_packs",
        "projects",
        "ritual_entries",
        "profiles",
    ]
    for table in tables:
        session.execute(text(f"DELETE FROM {table};"))
    session.commit()


def seed_profile(session) -> Profile:
    profile = session.query(Profile).order_by(Profile.id.asc()).first()
    if profile:
        return profile
    profile = Profile(
        name="Test User",
        why_primary="Build a calm system that protects focus and family time.",
        why_expanded="Best work, steady energy, and a clear weekly rhythm.",
        values_text="Presence, Courage, Craft, Health",
        energy_profile="morning",
        workday_start=time(8, 30),
        workday_end=time(17, 30),
        weekly_review_day="sunday",
        focus_block_preference="90",
    )
    session.add(profile)
    session.commit()
    return profile


def seed_projects(session) -> list[Project]:
    projects: list[Project] = []
    color_keys = [key for key, _ in PROJECT_COLOR_CHOICES]
    work_titles = [
        "Client launch plan",
        "Marketing site refresh",
        "Ops playbook cleanup",
        "Finance review",
        "Pipeline tune-up",
        "Quarterly strategy memo",
    ]
    personal_titles = [
        "Health reset",
        "Home studio tidy",
        "Family trip planning",
        "Reading habit",
    ]
    for idx, title in enumerate(work_titles):
        active = idx < 3
        projects.append(
            Project(
                title=title,
                category=ProjectCategory.WORK,
                status=ProjectStatus.ACTIVE if idx != 4 else ProjectStatus.PAUSED,
                size=ProjectSize.MODERATE,
                color_scheme=random.choice(color_keys),
                time_horizon="week" if active else "month",
                active_this_week=active,
                level_of_success=SuccessLevel.MODERATE,
                why_link_text="Moves the business forward without thrashing.",
            )
        )
    for idx, title in enumerate(personal_titles):
        active = idx < 2
        projects.append(
            Project(
                title=title,
                category=ProjectCategory.PERSONAL,
                status=ProjectStatus.ACTIVE,
                size=ProjectSize.LIGHT,
                color_scheme=random.choice(color_keys),
                time_horizon="week" if active else "quarter",
                active_this_week=active,
                level_of_success=SuccessLevel.SMALL,
                why_link_text="Protects home life and energy.",
            )
        )
    session.add_all(projects)
    session.commit()

    for project in projects[:3]:
        session.add(
            SuccessPack(
                project_id=project.id,
                guides="Coach A",
                peers="Peer B",
                supporters="Partner C",
                beneficiaries="Future me",
            )
        )
    session.commit()
    return projects


def seed_tasks(session, projects: list[Project]) -> list[Task]:
    tasks: list[Task] = []
    today = date.today()
    buckets = [
        WhenBucket.TODAY,
        WhenBucket.WEEK,
        WhenBucket.MONTH,
        WhenBucket.QUARTER,
        WhenBucket.LATER,
    ]
    block_types = [BlockType.FOCUS, BlockType.ADMIN, BlockType.SOCIAL, BlockType.RECOVERY]
    alignments = [Alignment.ALIGNED, Alignment.PARTIAL, Alignment.UNALIGNED]

    task_titles = [
        "Draft launch checklist",
        "Review copy edits",
        "Send stakeholder update",
        "Prep focus block outline",
        "Schedule workout",
        "Plan family calendar",
        "Collect metrics snapshot",
        "Refine weekly goals",
        "Clean up inbox",
        "Write decision memo",
        "Map next sprint tasks",
        "Confirm travel dates",
        "Block deep work session",
        "Triage support tickets",
        "Check energy baseline",
    ]

    inbox_buckets = {WhenBucket.LATER, WhenBucket.MONTH, WhenBucket.QUARTER}

    for idx in range(30):
        bucket = random.choice(buckets)
        is_inbox = bucket in inbox_buckets
        # Keep inbox-style buckets unprocessed (no project attached).
        project = None if is_inbox else random.choice(projects + [None])
        status = TaskStatus.PENDING
        completed_at = None
        if not is_inbox:
            if idx % 7 == 0:
                status = TaskStatus.DONE
                completed_at = datetime.utcnow() - timedelta(days=idx % 5)
            elif idx % 11 == 0:
                status = TaskStatus.ARCHIVED
            elif idx % 13 == 0:
                status = TaskStatus.CANCELLED

        scheduled_for = None
        if bucket in {WhenBucket.TODAY, WhenBucket.WEEK}:
            scheduled_for = today + timedelta(days=idx % 3)

        resurface_on = None
        if not is_inbox and bucket in {WhenBucket.QUARTER, WhenBucket.LATER}:
            resurface_on = today + timedelta(days=14 + idx)

        tasks.append(
            Task(
                project_id=project.id if project else None,
                verb_noun=random.choice(task_titles),
                description=None if is_inbox else "Test task for feature coverage.",
                in_inbox=is_inbox,
                when_bucket=bucket,
                block_type=None if is_inbox else random.choice(block_types),
                duration_minutes=None if is_inbox else random.choice([30, 45, 60, 90]),
                priority=None if is_inbox else random.choice([1, 2, 3]),
                frog=False if is_inbox else idx % 9 == 0,
                alignment=None if is_inbox else random.choice(alignments),
                status=status,
                scheduled_for=scheduled_for,
                owner_type=OwnerType.MINE if is_inbox else random.choice(
                    [OwnerType.MINE, OwnerType.SHARED, OwnerType.OPP]
                ),
                resurface_on=resurface_on,
                completed_at=completed_at,
            )
        )

    session.add_all(tasks)
    session.commit()
    return tasks


def seed_blocks(session, projects: list[Project], tasks: list[Task]) -> None:
    today = date.today()
    blocks = [
        Block(
            title="Deep work block",
            date=today,
            start_time=time(9, 0),
            end_time=time(10, 30),
            block_type=BlockType.FOCUS,
            project_id=projects[0].id,
            task_id=tasks[0].id,
            notes="Protect for best work.",
        ),
        Block(
            title="Admin sweep",
            date=today,
            start_time=time(11, 0),
            end_time=time(11, 45),
            block_type=BlockType.ADMIN,
            project_id=projects[1].id,
            notes="Clear low-energy tasks.",
        ),
        Block(
            title="Recovery walk",
            date=today + timedelta(days=1),
            start_time=time(15, 0),
            end_time=time(15, 30),
            block_type=BlockType.RECOVERY,
            notes="Reset for afternoon.",
        ),
    ]
    session.add_all(blocks)
    session.commit()


def seed_waiting_on(session, projects: list[Project]) -> None:
    waiting = [
        WaitingOn(
            description="Confirm vendor timelines",
            person="Alex",
            project_id=projects[0].id,
            last_followup=date.today() - timedelta(days=3),
        ),
        WaitingOn(
            description="Budget approval",
            person="Sam",
            project_id=projects[3].id,
            last_followup=date.today() - timedelta(days=7),
        ),
        WaitingOn(
            description="Contract signature",
            person="Jordan",
            project_id=projects[1].id,
            last_followup=date.today() + timedelta(days=2),
        ),
    ]
    session.add_all(waiting)
    session.commit()


def seed_rituals(session) -> None:
    today = date.today()
    entries = [
        RitualEntry(
            ritual_type=RitualType.MORNING,
            entry_date=today,
            grounding_movement="Stretch + walk",
            one_thing="Draft launch checklist",
            frog="Call vendor",
            gratitude="Clear schedule",
            energy="steady",
        ),
        RitualEntry(
            ritual_type=RitualType.MIDDAY,
            entry_date=today,
            focus_time_status="One focus block done",
            notes="Need to reset for afternoon.",
        ),
        RitualEntry(
            ritual_type=RitualType.EVENING,
            entry_date=today - timedelta(days=1),
            wins="Finished deep work block",
            adjustments="Less meetings on Tuesday",
        ),
    ]
    session.add_all(entries)
    session.commit()


def seed_health(session) -> None:
    metrics = {m.slug: m for m in session.query(HealthMetric).all()}
    today = date.today()

    def add_entry(slug: str, day_offset: int, value: float, notes: str | None = None) -> None:
        metric = metrics.get(slug)
        if not metric:
            return
        session.add(
            HealthEntry(
                metric_id=metric.id,
                entry_date=today - timedelta(days=day_offset),
                value=value,
                notes=notes,
            )
        )

    for i in range(14):
        add_entry("body_weight", i, 82.0 - i * 0.1)
        add_entry("resting_hr", i, 62 - i * 0.1)
        add_entry("sleep_hours", i, 7.2 + (i % 3) * 0.2)
        add_entry("steps", i, 8500 + i * 120)
        add_entry("protein_g", i, 140 + (i % 4) * 5)

    goals = [
        HealthGoal(
            title="Resting HR under 60",
            metric_id=metrics.get("resting_hr").id if metrics.get("resting_hr") else None,
            target_value=60,
            target_date=today + timedelta(days=60),
            notes="Morning resting average.",
        ),
        HealthGoal(
            title="Daily steps 10k average",
            metric_id=metrics.get("steps").id if metrics.get("steps") else None,
            target_value=10000,
            target_date=today + timedelta(days=45),
            notes="Walks after lunch.",
        ),
    ]
    session.add_all(goals)
    session.commit()


def seed_coach(session) -> None:
    convo = CoachConversation()
    session.add(convo)
    session.commit()
    messages = [
        CoachMessage(
            conversation_id=convo.id,
            role="user",
            content="Help me pick the One Thing.",
        ),
        CoachMessage(
            conversation_id=convo.id,
            role="assistant",
            content="Pick the task that moves your top project and protect one focus block.",
        ),
    ]
    session.add_all(messages)
    session.commit()


def seed_guidance(session) -> None:
    session.add(GuidanceEvent(code="weekly_review_done", context_json='{"wins":"Test win"}'))
    session.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed junk data into sfo.db for testing.")
    parser.add_argument("--reset", action="store_true", help="Delete existing data before seeding.")
    args = parser.parse_args()

    Base.metadata.create_all(bind=engine)
    ensure_task_owner_column()
    ensure_task_resurface_columns()
    ensure_block_title_column()
    ensure_ritual_table()
    ensure_ritual_columns()
    ensure_guidance_reminder_columns()
    ensure_project_color_column()

    session = SessionLocal()
    try:
        if args.reset:
            reset_db(session)
        ensure_health_metrics(session)
        seed_profile(session)
        projects = seed_projects(session)
        tasks = seed_tasks(session, projects)
        seed_blocks(session, projects, tasks)
        seed_waiting_on(session, projects)
        seed_rituals(session)
        seed_health(session)
        seed_coach(session)
        seed_guidance(session)
    finally:
        session.close()

    print("Seeded test data into sfo.db.")


if __name__ == "__main__":
    random.seed(42)
    main()
