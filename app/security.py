from __future__ import annotations

import hmac
import os
import secrets
from urllib.parse import quote_plus

from fastapi import HTTPException, Request, status

SESSION_USER_KEY = "user"
SESSION_CSRF_KEY = "csrf_token"


def ui_auth_enabled() -> bool:
    return bool(os.getenv("SFO_PASSWORD"))


def api_auth_enabled() -> bool:
    return ui_auth_enabled() or bool(os.getenv("SFO_API_TOKEN"))


def expected_username() -> str | None:
    return os.getenv("SFO_USERNAME")


def api_token() -> str | None:
    return os.getenv("SFO_API_TOKEN")


def _safe_compare(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


def verify_credentials(username: str | None, password: str) -> bool:
    expected_password = os.getenv("SFO_PASSWORD")
    if not expected_password:
        return False
    if not _safe_compare(password, expected_password):
        return False

    expected_user = expected_username()
    if expected_user:
        submitted = (username or "").strip()
        return _safe_compare(submitted, expected_user)
    return True


def _login_redirect(request: Request) -> None:
    next_url = request.url.path
    if request.url.query:
        next_url = f"{next_url}?{request.url.query}"
    encoded_next = quote_plus(next_url)
    raise HTTPException(
        status_code=status.HTTP_303_SEE_OTHER,
        headers={"Location": f"/login?next={encoded_next}"},
    )


def require_html_auth(request: Request) -> None:
    if not ui_auth_enabled():
        return
    if request.session.get(SESSION_USER_KEY):
        return
    _login_redirect(request)


def require_api_auth(request: Request) -> None:
    if not api_auth_enabled():
        return
    token = api_token()
    header_token = request.headers.get("x-api-key")
    if token and header_token and _safe_compare(header_token, token):
        return
    if request.session.get(SESSION_USER_KEY):
        return
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")


def is_authenticated(request: Request) -> bool:
    if not ui_auth_enabled():
        return False
    return bool(request.session.get(SESSION_USER_KEY))


def current_user(request: Request) -> str | None:
    return request.session.get(SESSION_USER_KEY)


def set_user_session(request: Request, username: str | None) -> None:
    request.session[SESSION_USER_KEY] = username or expected_username() or "user"
    request.session[SESSION_CSRF_KEY] = secrets.token_urlsafe(32)


def clear_user_session(request: Request) -> None:
    request.session.pop(SESSION_USER_KEY, None)
    request.session.pop(SESSION_CSRF_KEY, None)


def ensure_csrf_token(request: Request) -> str:
    token = request.session.get(SESSION_CSRF_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        request.session[SESSION_CSRF_KEY] = token
    return token


def is_safe_redirect(target: str | None) -> bool:
    if not target:
        return False
    if target.startswith("//"):
        return False
    if "://" in target:
        return False
    return target.startswith("/")


async def csrf_protect(request: Request) -> None:
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return

    token = api_token()
    header_token = request.headers.get("x-api-key")
    if token and header_token and _safe_compare(header_token, token):
        return

    session_token = request.session.get(SESSION_CSRF_KEY)
    if not session_token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF token missing")

    form_token = request.headers.get("x-csrf-token")
    if not form_token:
        content_type = request.headers.get("content-type", "")
        if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
            form = await request.form()
            form_token = form.get("csrf_token")

    if not form_token or not _safe_compare(str(form_token), str(session_token)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF validation failed")
