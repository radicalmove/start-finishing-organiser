from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from ..db import get_db
from ..security import csrf_protect, require_html_auth
from ..utils.coach import build_coach_context_json

router = APIRouter(dependencies=[Depends(require_html_auth), Depends(csrf_protect)])


@router.get("/guide", response_class=HTMLResponse)
def guide(request: Request, db: Session = Depends(get_db)):
    templates = request.app.state.templates
    guide_sections = [
        {
            "title": "Quick start",
            "items": [
                "Capture anything on your mind (Quick capture or Guided capture).",
                "Pick your weekly focus (4 work + 3 personal) in Weekly Review.",
                "Schedule blocks for your best work on the calendar.",
            ],
        },
        {
            "title": "Daily rhythm",
            "items": [
                "Morning check-in to choose your One Thing + Frog.",
                "Midday reset to adjust if the day drifted.",
                "Evening check-out to capture wins and reset tomorrow.",
            ],
        },
        {
            "title": "Weekly rhythm",
            "items": [
                "Review active projects and adjust to the 4+3 boundary.",
                "Resurface Month/Quarter/Later items into this week.",
                "Add focus blocks before admin or reactive work.",
            ],
        },
        {
            "title": "Key screens",
            "items": [
                "Home: Today tasks + calendar.",
                "Blocks: add time blocks or schedule tasks with duration.",
                "Waiting On: keep OPP items out of your head.",
            ],
        },
    ]

    coach_context_json = build_coach_context_json(
        request_path=str(request.url.path),
        screen_id="guide",
        screen_title="Guide",
        screen_data={"sections": guide_sections},
        db=db,
    )

    return templates.TemplateResponse(
        "guide.html",
        {
            "request": request,
            "guide_sections": guide_sections,
            "coach_context_json": coach_context_json,
        },
    )
