from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from ..security import (
    csrf_protect,
    expected_username,
    is_safe_redirect,
    require_html_auth,
    set_user_session,
    clear_user_session,
    ui_auth_enabled,
    verify_credentials,
)

router = APIRouter()


@router.get("/login", response_class=HTMLResponse)
def login(request: Request):
    if not ui_auth_enabled():
        return RedirectResponse(url="/", status_code=303)

    templates = request.app.state.templates
    next_url = request.query_params.get("next")
    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "form_error": request.query_params.get("error"),
            "next_url": next_url,
            "require_username": bool(expected_username()),
        },
    )


@router.post("/login", dependencies=[Depends(csrf_protect)])
def login_submit(
    request: Request,
    password: str = Form(...),
    username: str | None = Form(None),
    next_url: str | None = Form(None),
):
    if not ui_auth_enabled():
        return RedirectResponse(url="/", status_code=303)

    if not verify_credentials(username, password):
        templates = request.app.state.templates
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "form_error": "Invalid credentials.",
                "next_url": next_url,
                "require_username": bool(expected_username()),
            },
        )

    set_user_session(request, username)
    target = next_url if is_safe_redirect(next_url) else "/"
    return RedirectResponse(url=target, status_code=303)


@router.post(
    "/logout",
    dependencies=[Depends(require_html_auth), Depends(csrf_protect)],
)
def logout(request: Request):
    clear_user_session(request)
    return RedirectResponse(url="/login", status_code=303)
