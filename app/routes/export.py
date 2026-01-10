from __future__ import annotations

import csv
import io
import json
import zipfile
from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy.orm import Session, selectinload

from ..db import get_db
from ..models import (
    Block,
    CoachMessage,
    GuidanceEvent,
    GuidanceReminder,
    HealthEntry,
    HealthGoal,
    HealthMetric,
    Profile,
    Project,
    ProjectStatus,
    RitualEntry,
    Task,
    TaskStatus,
    WaitingOn,
)
from ..security import csrf_protect, require_html_auth
from ..utils.coach import build_coach_context_json

router = APIRouter(dependencies=[Depends(require_html_auth), Depends(csrf_protect)])


def _date_range(choice: str) -> tuple[date | None, date]:
    today = date.today()
    if choice == "week":
        return today - timedelta(days=7), today
    if choice == "month":
        return today - timedelta(days=30), today
    if choice == "quarter":
        return today - timedelta(days=90), today
    if choice == "year":
        return today - timedelta(days=365), today
    return None, today


def _dt_bounds(start: date | None, end: date) -> tuple[datetime | None, datetime]:
    start_dt = datetime.combine(start, time.min) if start else None
    end_dt = datetime.combine(end, time.max)
    return start_dt, end_dt


def _csv_bytes(rows: list[dict], fieldnames: list[str]) -> bytes:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return output.getvalue().encode("utf-8")


def _json_bytes(payload: object) -> bytes:
    return json.dumps(payload, ensure_ascii=True, default=str, indent=2).encode("utf-8")


def _profile_payload(profile: Profile | None) -> list[dict]:
    if not profile:
        return []
    return [
        {
            "id": profile.id,
            "name": profile.name,
            "why_primary": profile.why_primary,
            "why_expanded": profile.why_expanded,
            "values_text": profile.values_text,
            "energy_profile": profile.energy_profile,
            "workday_start": profile.workday_start.isoformat() if profile.workday_start else None,
            "workday_end": profile.workday_end.isoformat() if profile.workday_end else None,
            "weekly_review_day": profile.weekly_review_day,
            "focus_block_preference": profile.focus_block_preference,
            "created_at": profile.created_at,
            "updated_at": profile.updated_at,
        }
    ]


def _project_payload(projects: list[Project]) -> list[dict]:
    payload = []
    for project in projects:
        payload.append(
            {
                "id": project.id,
                "title": project.title,
                "description": project.description,
                "category": project.category.value if project.category else None,
                "status": project.status.value if project.status else None,
                "size": project.size.value if project.size else None,
                "time_horizon": project.time_horizon,
                "start_date": project.start_date,
                "target_date": project.target_date,
                "level_of_success": project.level_of_success.value if project.level_of_success else None,
                "why_link_text": project.why_link_text,
                "drag_points_notes": project.drag_points_notes,
                "active_this_week": project.active_this_week,
                "created_at": project.created_at,
                "updated_at": project.updated_at,
            }
        )
    return payload


def _task_payload(tasks: list[Task]) -> list[dict]:
    payload = []
    for task in tasks:
        payload.append(
            {
                "id": task.id,
                "verb_noun": task.verb_noun,
                "description": task.description,
                "status": task.status.value if task.status else None,
                "when_bucket": task.when_bucket.value if task.when_bucket else None,
                "block_type": task.block_type.value if task.block_type else None,
                "duration_minutes": task.duration_minutes,
                "priority": task.priority,
                "frog": task.frog,
                "alignment": task.alignment.value if task.alignment else None,
                "scheduled_for": task.scheduled_for,
                "project_id": task.project_id,
                "project_title": task.project.title if task.project else None,
                "completed_at": task.completed_at,
                "created_at": task.created_at,
            }
        )
    return payload


def _block_payload(blocks: list[Block]) -> list[dict]:
    payload = []
    for block in blocks:
        payload.append(
            {
                "id": block.id,
                "title": block.title,
                "date": block.date,
                "start_time": block.start_time,
                "end_time": block.end_time,
                "block_type": block.block_type.value if block.block_type else None,
                "project_id": block.project_id,
                "project_title": block.project.title if block.project else None,
                "task_id": block.task_id,
                "notes": block.notes,
                "created_at": block.created_at,
            }
        )
    return payload


def _ritual_payload(entries: list[RitualEntry]) -> list[dict]:
    payload = []
    for entry in entries:
        payload.append(
            {
                "id": entry.id,
                "ritual_type": entry.ritual_type.value if entry.ritual_type else None,
                "entry_date": entry.entry_date,
                "grounding_movement": entry.grounding_movement,
                "supplements_done": entry.supplements_done,
                "plan_review": entry.plan_review,
                "reality_scan": entry.reality_scan,
                "focus_time_status": entry.focus_time_status,
                "one_thing": entry.one_thing,
                "frog": entry.frog,
                "gratitude": entry.gratitude,
                "anticipation": entry.anticipation,
                "why_reflection": entry.why_reflection,
                "why_expanded": entry.why_expanded,
                "block_plan": entry.block_plan,
                "admin_plan": entry.admin_plan,
                "emotional_intent": entry.emotional_intent,
                "wins": entry.wins,
                "adjustments": entry.adjustments,
                "energy": entry.energy,
                "notes": entry.notes,
                "created_at": entry.created_at,
            }
        )
    return payload


def _waiting_payload(rows: list[WaitingOn]) -> list[dict]:
    payload = []
    for row in rows:
        payload.append(
            {
                "id": row.id,
                "description": row.description,
                "person": row.person,
                "project_id": row.project_id,
                "project_title": row.project.title if row.project else None,
                "created_at": row.created_at,
                "last_followup": row.last_followup,
            }
        )
    return payload


def _health_metric_payload(metrics: list[HealthMetric]) -> list[dict]:
    return [
        {
            "id": metric.id,
            "name": metric.name,
            "slug": metric.slug,
            "category": metric.category.value if metric.category else None,
            "unit": metric.unit,
            "description": metric.description,
            "target_direction": metric.target_direction,
            "is_key": metric.is_key,
            "created_at": metric.created_at,
        }
        for metric in metrics
    ]


def _health_entry_payload(entries: list[HealthEntry]) -> list[dict]:
    return [
        {
            "id": entry.id,
            "metric_id": entry.metric_id,
            "metric_name": entry.metric.name if entry.metric else None,
            "entry_date": entry.entry_date,
            "value": entry.value,
            "notes": entry.notes,
            "created_at": entry.created_at,
        }
        for entry in entries
    ]


def _health_goal_payload(goals: list[HealthGoal]) -> list[dict]:
    return [
        {
            "id": goal.id,
            "title": goal.title,
            "metric_id": goal.metric_id,
            "metric_name": goal.metric.name if goal.metric else None,
            "target_value": goal.target_value,
            "target_date": goal.target_date,
            "notes": goal.notes,
            "created_at": goal.created_at,
        }
        for goal in goals
    ]


def _coach_payload(messages: list[CoachMessage]) -> list[dict]:
    return [
        {
            "id": message.id,
            "conversation_id": message.conversation_id,
            "role": message.role,
            "content": message.content,
            "context_json": message.context_json,
            "actions_json": message.actions_json,
            "created_at": message.created_at,
        }
        for message in messages
    ]


def _reminder_payload(reminders: list[GuidanceReminder]) -> list[dict]:
    return [
        {
            "id": reminder.id,
            "code": reminder.code,
            "title": reminder.title,
            "body": reminder.body,
            "period_start": reminder.period_start,
            "due_on": reminder.due_on,
            "completed_at": reminder.completed_at,
            "acknowledged_at": reminder.acknowledged_at,
            "snoozed_until": reminder.snoozed_until,
            "last_shown_at": reminder.last_shown_at,
            "created_at": reminder.created_at,
        }
        for reminder in reminders
    ]


def _event_payload(events: list[GuidanceEvent]) -> list[dict]:
    return [
        {
            "id": event.id,
            "code": event.code,
            "context_json": event.context_json,
            "created_at": event.created_at,
        }
        for event in events
    ]


@router.get("/export", response_class=HTMLResponse)
def export_page(request: Request, db: Session = Depends(get_db)):
    templates = request.app.state.templates
    coach_context_json = build_coach_context_json(
        request_path=str(request.url.path),
        screen_id="export",
        screen_title="Export data",
        screen_data={},
        db=db,
    )
    return templates.TemplateResponse(
        "export.html",
        {"request": request, "coach_context_json": coach_context_json},
    )


@router.post("/export")
def export_data(
    range_choice: str = Form("all"),
    include_profile: str | None = Form(None),
    include_projects: str | None = Form(None),
    include_tasks: str | None = Form(None),
    include_blocks: str | None = Form(None),
    include_rituals: str | None = Form(None),
    include_waiting: str | None = Form(None),
    include_health: str | None = Form(None),
    include_coach: str | None = Form(None),
    include_guidance: str | None = Form(None),
    db: Session = Depends(get_db),
):
    start_date, end_date = _date_range(range_choice)
    start_dt, end_dt = _dt_bounds(start_date, end_date)
    created_at = datetime.utcnow().isoformat()

    include_profile = bool(include_profile)
    include_projects = bool(include_projects)
    include_tasks = bool(include_tasks)
    include_blocks = bool(include_blocks)
    include_rituals = bool(include_rituals)
    include_waiting = bool(include_waiting)
    include_health = bool(include_health)
    include_coach = bool(include_coach)
    include_guidance = bool(include_guidance)

    payload = {"metadata": {"created_at": created_at, "range": range_choice}}
    files: dict[str, bytes] = {}

    if include_profile:
        profile = db.query(Profile).order_by(Profile.id.asc()).first()
        profile_rows = _profile_payload(profile)
        payload["profile"] = profile_rows
        files["profile.json"] = _json_bytes(profile_rows)
        if profile_rows:
            files["profile.csv"] = _csv_bytes(profile_rows, list(profile_rows[0].keys()))

    if include_projects:
        projects_query = db.query(Project).filter(Project.status.notin_([ProjectStatus.COMPLETED, ProjectStatus.ARCHIVED]))
        if start_dt:
            projects_query = projects_query.filter(Project.created_at >= start_dt)
        projects = projects_query.order_by(Project.created_at.desc()).all()
        active_projects = [
            p for p in db.query(Project).filter(Project.status == ProjectStatus.ACTIVE).all()
            if p not in projects
        ]
        projects = list({p.id: p for p in projects + active_projects}.values())
        project_rows = _project_payload(projects)
        payload["projects"] = project_rows
        files["projects.json"] = _json_bytes(project_rows)
        if project_rows:
            files["projects.csv"] = _csv_bytes(project_rows, list(project_rows[0].keys()))

    if include_tasks:
        tasks_query = db.query(Task).options(selectinload(Task.project)).filter(
            Task.status.notin_([TaskStatus.DONE, TaskStatus.ARCHIVED, TaskStatus.CANCELLED])
        )
        if start_dt:
            tasks_query = tasks_query.filter(Task.created_at >= start_dt)
        tasks = tasks_query.order_by(Task.created_at.desc()).all()
        active_tasks = db.query(Task).options(selectinload(Task.project)).filter(
            Task.status.in_([TaskStatus.PENDING, TaskStatus.IN_PROGRESS])
        ).all()
        tasks = list({t.id: t for t in tasks + active_tasks}.values())
        task_rows = _task_payload(tasks)
        payload["tasks"] = task_rows
        files["tasks.json"] = _json_bytes(task_rows)
        if task_rows:
            files["tasks.csv"] = _csv_bytes(task_rows, list(task_rows[0].keys()))

    if include_blocks:
        blocks_query = db.query(Block).options(selectinload(Block.project))
        if start_date:
            blocks_query = blocks_query.filter(Block.date >= start_date, Block.date <= end_date)
        blocks = blocks_query.order_by(Block.date.desc()).all()
        block_rows = _block_payload(blocks)
        payload["blocks"] = block_rows
        files["blocks.json"] = _json_bytes(block_rows)
        if block_rows:
            files["blocks.csv"] = _csv_bytes(block_rows, list(block_rows[0].keys()))

    if include_rituals:
        rituals_query = db.query(RitualEntry)
        if start_date:
            rituals_query = rituals_query.filter(
                RitualEntry.entry_date >= start_date, RitualEntry.entry_date <= end_date
            )
        rituals = rituals_query.order_by(RitualEntry.entry_date.desc()).all()
        ritual_rows = _ritual_payload(rituals)
        payload["ritual_entries"] = ritual_rows
        files["ritual_entries.json"] = _json_bytes(ritual_rows)
        if ritual_rows:
            files["ritual_entries.csv"] = _csv_bytes(ritual_rows, list(ritual_rows[0].keys()))

    if include_waiting:
        waiting_query = db.query(WaitingOn).options(selectinload(WaitingOn.project))
        if start_dt:
            waiting_query = waiting_query.filter(WaitingOn.created_at >= start_dt)
        waiting_rows = _waiting_payload(waiting_query.order_by(WaitingOn.created_at.desc()).all())
        payload["waiting_on"] = waiting_rows
        files["waiting_on.json"] = _json_bytes(waiting_rows)
        if waiting_rows:
            files["waiting_on.csv"] = _csv_bytes(waiting_rows, list(waiting_rows[0].keys()))

    if include_health:
        entries_query = db.query(HealthEntry).options(selectinload(HealthEntry.metric))
        if start_date:
            entries_query = entries_query.filter(
                HealthEntry.entry_date >= start_date, HealthEntry.entry_date <= end_date
            )
        entries = entries_query.order_by(HealthEntry.entry_date.desc()).all()
        entry_rows = _health_entry_payload(entries)
        goals_query = db.query(HealthGoal).options(selectinload(HealthGoal.metric))
        if start_dt:
            goals_query = goals_query.filter(
                (HealthGoal.created_at >= start_dt)
                | (HealthGoal.target_date.isnot(None) & (HealthGoal.target_date >= start_date))
            )
        goals = goals_query.order_by(HealthGoal.created_at.desc()).all()
        goal_rows = _health_goal_payload(goals)
        metric_ids = {row["metric_id"] for row in entry_rows if row.get("metric_id")}
        metric_ids.update({row["metric_id"] for row in goal_rows if row.get("metric_id")})
        metrics_query = db.query(HealthMetric)
        if metric_ids and range_choice != "all":
            metrics_query = metrics_query.filter(HealthMetric.id.in_(metric_ids))
        metrics = metrics_query.order_by(HealthMetric.name.asc()).all()
        metric_rows = _health_metric_payload(metrics)
        payload["health_entries"] = entry_rows
        payload["health_goals"] = goal_rows
        payload["health_metrics"] = metric_rows
        files["health_entries.json"] = _json_bytes(entry_rows)
        files["health_goals.json"] = _json_bytes(goal_rows)
        files["health_metrics.json"] = _json_bytes(metric_rows)
        if entry_rows:
            files["health_entries.csv"] = _csv_bytes(entry_rows, list(entry_rows[0].keys()))
        if goal_rows:
            files["health_goals.csv"] = _csv_bytes(goal_rows, list(goal_rows[0].keys()))
        if metric_rows:
            files["health_metrics.csv"] = _csv_bytes(metric_rows, list(metric_rows[0].keys()))

    if include_coach:
        messages_query = db.query(CoachMessage)
        if start_dt:
            messages_query = messages_query.filter(CoachMessage.created_at >= start_dt)
        messages = messages_query.order_by(CoachMessage.created_at.desc()).all()
        message_rows = _coach_payload(messages)
        payload["coach_messages"] = message_rows
        files["coach_messages.json"] = _json_bytes(message_rows)
        if message_rows:
            files["coach_messages.csv"] = _csv_bytes(message_rows, list(message_rows[0].keys()))

    if include_guidance:
        reminders_query = db.query(GuidanceReminder)
        if start_dt:
            reminders_query = reminders_query.filter(GuidanceReminder.created_at >= start_dt)
        reminders = reminders_query.order_by(GuidanceReminder.created_at.desc()).all()
        reminder_rows = _reminder_payload(reminders)
        events_query = db.query(GuidanceEvent)
        if start_dt:
            events_query = events_query.filter(GuidanceEvent.created_at >= start_dt)
        events = events_query.order_by(GuidanceEvent.created_at.desc()).all()
        event_rows = _event_payload(events)
        payload["guidance_reminders"] = reminder_rows
        payload["guidance_events"] = event_rows
        files["guidance_reminders.json"] = _json_bytes(reminder_rows)
        files["guidance_events.json"] = _json_bytes(event_rows)
        if reminder_rows:
            files["guidance_reminders.csv"] = _csv_bytes(reminder_rows, list(reminder_rows[0].keys()))
        if event_rows:
            files["guidance_events.csv"] = _csv_bytes(event_rows, list(event_rows[0].keys()))

    files["export.json"] = _json_bytes(payload)
    summary = {
        "created_at": created_at,
        "range": range_choice,
        "included": [
            key
            for key, flag in {
                "profile": include_profile,
                "projects": include_projects,
                "tasks": include_tasks,
                "blocks": include_blocks,
                "rituals": include_rituals,
                "waiting_on": include_waiting,
                "health": include_health,
                "coach": include_coach,
                "guidance": include_guidance,
            }.items()
            if flag
        ],
    }
    files["summary.json"] = _json_bytes(summary)

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for filename, data in files.items():
            zf.writestr(filename, data)
    buffer.seek(0)

    filename = f"sfo_export_{date.today().isoformat()}.zip"
    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
