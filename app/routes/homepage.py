from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from urllib.parse import quote_plus

from ..db import get_db
from ..models import (
    Project,
    ProjectStatus,
    ProjectCategory,
    Task,
    WhenBucket,
    Block,
    BlockType,
)

router = APIRouter()


def _enforce_weekly_cap(db: Session, category: ProjectCategory, make_active: bool) -> None:
    """Prevent adding more than 4 work or 3 personal active projects per week."""
    if not make_active:
        return
    cap = 4 if category == ProjectCategory.WORK else 3
    current = (
        db.query(Project)
        .filter(Project.category == category, Project.active_this_week.is_(True))
        .count()
    )
    if current >= cap:
        raise HTTPException(
            status_code=400,
            detail=f"Weekly cap reached for {category.value} projects ({current}/{cap}).",
        )


def _compose_why_text(free_text: str | None, tags: list[str] | None) -> str | None:
    """Combine quick Why tags with free text into one stored field."""
    tag_part = ""
    if tags:
        tag_part = "Tags: " + ", ".join([t for t in tags if t.strip()])
    parts = [p for p in [free_text or None, tag_part or None] if p]
    return "\n".join(parts) if parts else None


@router.get("/", response_class=HTMLResponse)
def landing(request: Request, db: Session = Depends(get_db)):
    templates = request.app.state.templates

    projects = (
        db.query(Project)
        .filter(Project.status != ProjectStatus.ARCHIVED)
        .order_by(Project.active_this_week.desc(), Project.created_at.desc())
        .all()
    )
    today_tasks = (
        db.query(Task)
        .filter(Task.when_bucket == WhenBucket.TODAY)
        .order_by(Task.block_type.asc().nulls_last(), Task.priority.asc().nulls_last())
        .all()
    )
    week_blocks = (
        db.query(Block)
        .order_by(Block.date.asc(), Block.start_time.asc().nulls_last())
        .all()
    )

    # Soft enforcement snapshot for the 4 work + 3 personal rule
    weekly_work = [p for p in projects if p.active_this_week and p.category == ProjectCategory.WORK]
    weekly_personal = [
        p for p in projects if p.active_this_week and p.category == ProjectCategory.PERSONAL
    ]

    return templates.TemplateResponse(
        "home.html",
        {
            "request": request,
            "projects": projects,
            "today_tasks": today_tasks,
            "week_blocks": week_blocks,
            "weekly_work_count": len(weekly_work),
            "weekly_personal_count": len(weekly_personal),
            "form_error": request.query_params.get("error"),
        },
    )


@router.post("/projects/form")
def create_project(
    title: str = Form(...),
    category: ProjectCategory = Form(ProjectCategory.WORK),
    time_horizon: str = Form("week"),
    include_this_week: str = Form("yes"),
    description: str | None = Form(None),
    why_link_text: str | None = Form(None),
    why_tags: list[str] | None = Form(None),
    db: Session = Depends(get_db),
):
    active_this_week = include_this_week.lower() == "yes" or time_horizon == "week"
    if active_this_week:
        try:
            _enforce_weekly_cap(db, category, True)
        except HTTPException as exc:
            msg = quote_plus(str(exc.detail))
            return RedirectResponse(url=f"/?error={msg}", status_code=303)

    project = Project(
        title=title.strip(),
        category=category,
        description=description or None,
        active_this_week=active_this_week,
        why_link_text=_compose_why_text(why_link_text, why_tags),
        time_horizon=time_horizon,
    )
    db.add(project)
    db.commit()
    return RedirectResponse(url="/", status_code=303)


@router.post("/tasks/form")
def create_task(
    verb_noun: str = Form(...),
    project_id: str | None = Form(""),
    description: str | None = Form(None),
    when_bucket: WhenBucket = Form(WhenBucket.TODAY),
    block_type: str | None = Form(""),
    frog: bool = Form(False),
    db: Session = Depends(get_db),
):
    pid = int(project_id) if project_id not in (None, "", "null") else None
    btype = block_type if block_type not in (None, "", "null") else None

    task = Task(
        verb_noun=verb_noun.strip(),
        project_id=pid,
        description=description or None,
        when_bucket=when_bucket,
        block_type=BlockType(btype) if btype else None,
        frog=frog,
    )
    db.add(task)
    db.commit()
    return RedirectResponse(url="/", status_code=303)
