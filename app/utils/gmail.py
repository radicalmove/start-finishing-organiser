from __future__ import annotations

import base64
import html
import logging
import os
import re
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parseaddr, parsedate_to_datetime

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from ..db import SessionLocal
from ..models import EmailMessage, EmailSyncState, Task, WhenBucket

try:
    from google.auth.transport.requests import Request
    from google.auth.exceptions import RefreshError
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError

    GOOGLE_AVAILABLE = True
except Exception:  # pragma: no cover - optional dependency guard
    GOOGLE_AVAILABLE = False
    Credentials = None
    InstalledAppFlow = None
    Request = None
    RefreshError = Exception
    build = None
    HttpError = Exception

GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
DEFAULT_CLIENT_SECRETS = "~/.config/sfo/gmail_credentials.json"
DEFAULT_TOKEN_PATH = "~/.config/sfo/gmail_token.json"
DEFAULT_POLL_SECONDS = 300
DEFAULT_MAX_PER_SYNC = 50
DEFAULT_BACKFILL_DAYS = 0

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GmailSettings:
    enabled: bool
    client_secrets_path: str
    token_path: str
    poll_seconds: int
    max_per_sync: int
    backfill_days: int
    work_domain: str

    @classmethod
    def from_env(cls) -> "GmailSettings":
        enabled = _parse_bool(os.getenv("SFO_GMAIL_ENABLED"))
        client_secrets = os.getenv("SFO_GMAIL_CLIENT_SECRETS", DEFAULT_CLIENT_SECRETS)
        token_path = os.getenv("SFO_GMAIL_TOKEN_PATH", DEFAULT_TOKEN_PATH)
        poll_seconds = _parse_int(os.getenv("SFO_GMAIL_POLL_SECONDS"), DEFAULT_POLL_SECONDS)
        max_per_sync = _parse_int(os.getenv("SFO_GMAIL_MAX_PER_SYNC"), DEFAULT_MAX_PER_SYNC)
        backfill_days = _parse_int(os.getenv("SFO_GMAIL_BACKFILL_DAYS"), DEFAULT_BACKFILL_DAYS)
        work_domain = (os.getenv("SFO_GMAIL_WORK_DOMAIN") or "").strip().lstrip("@")
        return cls(
            enabled=enabled,
            client_secrets_path=_expand_path(client_secrets),
            token_path=_expand_path(token_path),
            poll_seconds=max(30, poll_seconds),
            max_per_sync=max(1, max_per_sync),
            backfill_days=max(0, backfill_days),
            work_domain=work_domain,
        )


class GmailHistoryTooOld(RuntimeError):
    pass


def start_gmail_sync_loop() -> None:
    settings = GmailSettings.from_env()
    if not settings.enabled:
        return
    if not GOOGLE_AVAILABLE:
        logger.warning("Gmail sync enabled but google auth libraries are missing.")
        return
    if not _credentials_available(settings):
        logger.warning("Gmail sync enabled but OAuth credentials are missing.")
        return

    thread = threading.Thread(
        target=_sync_loop,
        args=(settings,),
        name="gmail-sync",
        daemon=True,
    )
    thread.start()


def authorize_gmail(settings: GmailSettings) -> str:
    if not GOOGLE_AVAILABLE:
        raise RuntimeError("Gmail libraries are not installed.")
    if not os.path.exists(settings.client_secrets_path):
        raise FileNotFoundError(f"Missing client secrets at {settings.client_secrets_path}")
    flow = InstalledAppFlow.from_client_secrets_file(settings.client_secrets_path, GMAIL_SCOPES)
    creds = flow.run_local_server(port=0)
    _save_credentials(settings.token_path, creds)
    return settings.token_path


def sync_gmail_inbox(db: Session, settings: GmailSettings) -> dict:
    if not settings.enabled:
        return {"status": "disabled", "imported": 0}
    service = _gmail_service(settings)
    if service is None:
        return {"status": "missing_credentials", "imported": 0}

    state = _get_sync_state(db)
    imported = 0
    skipped = 0
    errors = 0
    history_updated = False

    if not state.last_history_id:
        if settings.backfill_days:
            backfill = _backfill_messages(service, db, settings)
            imported += backfill["imported"]
            skipped += backfill["skipped"]
            errors += backfill["errors"]
        profile = service.users().getProfile(userId="me").execute()
        state.last_history_id = profile.get("historyId")
        state.last_sync_at = datetime.now(timezone.utc)
        db.add(state)
        db.commit()
        return {
            "status": "initialized",
            "imported": imported,
            "skipped": skipped,
            "errors": errors,
        }

    try:
        message_ids, checkpoint_history_id, truncated = _history_message_ids(
            service,
            state.last_history_id,
            settings.max_per_sync,
        )
    except GmailHistoryTooOld:
        profile = service.users().getProfile(userId="me").execute()
        state.last_history_id = profile.get("historyId")
        state.last_sync_at = datetime.now(timezone.utc)
        db.add(state)
        db.commit()
        return {"status": "reset_history", "imported": 0, "skipped": 0, "errors": 0}

    for message_id in message_ids:
        outcome = _import_message(service, db, message_id, settings)
        if outcome == "imported":
            imported += 1
        elif outcome == "skipped":
            skipped += 1
        else:
            errors += 1

    if checkpoint_history_id:
        state.last_history_id = checkpoint_history_id
        history_updated = True
    state.last_sync_at = datetime.now(timezone.utc)
    db.add(state)
    db.commit()

    return {
        "status": "ok",
        "imported": imported,
        "skipped": skipped,
        "errors": errors,
        "history_updated": history_updated,
        "truncated": truncated,
    }


def _sync_loop(settings: GmailSettings) -> None:
    while True:
        db = SessionLocal()
        try:
            sync_gmail_inbox(db, settings)
        except Exception:
            logger.exception("Gmail sync failed.")
            db.rollback()
        finally:
            db.close()
        time.sleep(settings.poll_seconds)


def _gmail_service(settings: GmailSettings):
    creds = _load_credentials(settings)
    if creds is None:
        return None
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def _load_credentials(settings: GmailSettings):
    if not GOOGLE_AVAILABLE:
        return None
    if not os.path.exists(settings.token_path):
        return None
    try:
        creds = Credentials.from_authorized_user_file(settings.token_path, GMAIL_SCOPES)
    except Exception:
        logger.warning(
            "Gmail token file could not be read at %s. Re-authorize with python3 scripts/gmail_auth.py",
            settings.token_path,
        )
        return None
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            _save_credentials(settings.token_path, creds)
        except RefreshError as exc:
            logger.warning(
                "Gmail token refresh failed (%s). Re-authorize with python3 scripts/gmail_auth.py",
                exc,
            )
            return None
        except Exception:
            logger.exception("Unexpected Gmail token refresh failure.")
            return None
    if not creds or not creds.valid:
        logger.warning(
            "Gmail token is invalid. Re-authorize with python3 scripts/gmail_auth.py"
        )
        return None
    return creds


def _save_credentials(path: str, creds) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(creds.to_json())


def _credentials_available(settings: GmailSettings) -> bool:
    return os.path.exists(settings.client_secrets_path) and os.path.exists(settings.token_path)


def _get_sync_state(db: Session) -> EmailSyncState:
    state = db.query(EmailSyncState).filter(EmailSyncState.provider == "gmail").first()
    if state:
        return state
    state = EmailSyncState(provider="gmail")
    db.add(state)
    db.commit()
    return state


def _history_message_ids(service, start_history_id: str, max_results: int):
    message_ids: list[str] = []
    seen: set[str] = set()
    page_token = None
    checkpoint_history_id = start_history_id
    truncated = False

    while True:
        remaining = max_results - len(message_ids)
        if remaining <= 0:
            truncated = True
            break
        try:
            resp = (
                service.users()
                .history()
                .list(
                    userId="me",
                    startHistoryId=start_history_id,
                    historyTypes=["messageAdded"],
                    maxResults=min(500, remaining),
                    pageToken=page_token,
                )
                .execute()
            )
        except HttpError as exc:
            if getattr(exc, "status_code", None) == 404 or getattr(exc, "resp", None) and exc.resp.status == 404:
                raise GmailHistoryTooOld() from exc
            raise

        response_history_id = resp.get("historyId")
        history_rows = resp.get("history", [])
        if not history_rows and response_history_id:
            checkpoint_history_id = str(response_history_id)

        for history in history_rows:
            if len(message_ids) >= max_results:
                truncated = True
                break
            history_id = history.get("id")
            for added in history.get("messagesAdded", []):
                message = added.get("message") or {}
                message_id = message.get("id")
                if message_id and message_id not in seen:
                    seen.add(message_id)
                    message_ids.append(message_id)
            if history_id is not None:
                checkpoint_history_id = str(history_id)
            if len(message_ids) >= max_results:
                truncated = True
                break

        page_token = resp.get("nextPageToken")
        if truncated or not page_token:
            if not truncated and response_history_id:
                checkpoint_history_id = str(response_history_id)
            break

    return message_ids, checkpoint_history_id, truncated


def _backfill_messages(service, db: Session, settings: GmailSettings) -> dict:
    query = f"in:inbox newer_than:{settings.backfill_days}d"
    message_ids = _list_message_ids(service, query, settings.max_per_sync)
    imported = 0
    skipped = 0
    errors = 0
    for message_id in message_ids:
        outcome = _import_message(service, db, message_id, settings)
        if outcome == "imported":
            imported += 1
        elif outcome == "skipped":
            skipped += 1
        else:
            errors += 1
    return {"imported": imported, "skipped": skipped, "errors": errors}


def _list_message_ids(service, query: str, max_results: int) -> list[str]:
    message_ids: list[str] = []
    page_token = None
    while True:
        remaining = max_results - len(message_ids)
        if remaining <= 0:
            break
        resp = (
            service.users()
            .messages()
            .list(userId="me", q=query, maxResults=min(500, remaining), pageToken=page_token)
            .execute()
        )
        for message in resp.get("messages", []):
            msg_id = message.get("id")
            if msg_id:
                message_ids.append(msg_id)
        page_token = resp.get("nextPageToken")
        if not page_token or len(message_ids) >= max_results:
            break
    return message_ids


def _import_message(service, db: Session, message_id: str, settings: GmailSettings) -> str:
    if db.query(EmailMessage).filter(EmailMessage.message_id == message_id).first():
        return "skipped"
    try:
        message = (
            service.users()
            .messages()
            .get(userId="me", id=message_id, format="full")
            .execute()
        )
    except HttpError as exc:
        status = getattr(exc, "status_code", None)
        if status is None and getattr(exc, "resp", None) is not None:
            status = exc.resp.status
        if status == 404:
            logger.info("Gmail message %s not found (likely deleted); skipping.", message_id)
            return "skipped"
        logger.exception("Failed to fetch Gmail message %s", message_id)
        return "error"
    except Exception:
        logger.exception("Failed to fetch Gmail message %s", message_id)
        return "error"

    headers = {h.get("name", "").lower(): h.get("value") for h in message.get("payload", {}).get("headers", [])}
    labels = set(message.get("labelIds", []))
    if "INBOX" not in labels:
        return "skipped"
    subject = (headers.get("subject") or "").strip()
    from_header = headers.get("from") or ""
    date_header = headers.get("date") or ""
    snippet = (message.get("snippet") or "").strip()
    body_text = _extract_message_body(message.get("payload") or {})
    thread_id = message.get("threadId")

    from_name, from_email = _parse_sender(from_header)
    received_at = _parse_received_at(message.get("internalDate"), date_header)
    is_work = _is_work_sender(from_email, settings.work_domain)
    title = _build_task_title(subject, from_name, from_email, is_work)
    description = _build_task_description(
        subject,
        from_name,
        from_email,
        snippet,
        received_at,
        body_text,
    )

    task = Task(
        verb_noun=title,
        description=description,
        in_inbox=True,
        when_bucket=WhenBucket.LATER,
        block_type=None,
        duration_minutes=None,
        frog=False,
    )
    db.add(task)
    db.flush()
    email_message = EmailMessage(
        message_id=message_id,
        thread_id=thread_id,
        from_name=from_name,
        from_email=from_email,
        subject=subject or None,
        snippet=snippet or None,
        received_at=received_at,
        task_id=task.id,
    )
    db.add(email_message)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        detail = str(exc).lower()
        if "unique constraint failed: email_messages.message_id" in detail:
            logger.info("Gmail message %s already imported by another sync worker; skipping.", message_id)
            return "skipped"
        logger.exception("Failed to store Gmail message %s", message_id)
        return "error"
    except Exception:
        db.rollback()
        logger.exception("Failed to store Gmail message %s", message_id)
        return "error"

    try:
        service.users().messages().modify(
            userId="me",
            id=message_id,
            body={"removeLabelIds": ["UNREAD"]},
        ).execute()
    except Exception:
        logger.exception("Failed to mark Gmail message as read: %s", message_id)
    return "imported"


def _build_task_title(subject: str, from_name: str | None, from_email: str | None, is_work: bool) -> str:
    if subject:
        base = subject.strip()
    else:
        sender = from_name or from_email or "Unknown sender"
        base = f"Email from {sender}"
    if is_work:
        base = f"[Work] {base}"
    return _clamp(base, 200)


def _build_task_description(
    subject: str,
    from_name: str | None,
    from_email: str | None,
    snippet: str,
    received_at: datetime | None,
    body_text: str | None,
) -> str | None:
    lines: list[str] = []
    if from_name or from_email:
        if from_name and from_email:
            lines.append(f"From: {from_name} <{from_email}>")
        else:
            lines.append(f"From: {from_name or from_email}")
    if subject:
        lines.append(f"Subject: {subject}")
    if received_at:
        lines.append(f"Received: {received_at.isoformat()}")
    body = (body_text or "").strip()
    if body:
        if lines:
            lines.append("")
        lines.append(body)
    elif snippet:
        if lines:
            lines.append("")
        lines.append(snippet)
    if not lines:
        return None
    return "\n".join(lines)


def _parse_sender(from_header: str) -> tuple[str | None, str | None]:
    name, email_addr = parseaddr(from_header)
    name = name.strip() or None
    email_addr = email_addr.strip() or None
    return name, email_addr


def _parse_received_at(internal_date: str | None, date_header: str) -> datetime | None:
    if internal_date and internal_date.isdigit():
        return datetime.fromtimestamp(int(internal_date) / 1000, tz=timezone.utc)
    if date_header:
        try:
            parsed = parsedate_to_datetime(date_header)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed
        except Exception:
            return None
    return None


def _extract_message_body(payload: dict) -> str | None:
    parts: list[tuple[str, str]] = []

    def walk(node: dict) -> None:
        if not node:
            return
        mime = (node.get("mimeType") or "").lower()
        body = node.get("body") or {}
        data = body.get("data")
        if data and mime.startswith("text/"):
            parts.append((mime, data))
        for child in node.get("parts", []) or []:
            walk(child)

    walk(payload)
    plain = next((data for mime, data in parts if mime.startswith("text/plain")), None)
    html_data = next((data for mime, data in parts if mime.startswith("text/html")), None)
    raw = plain or html_data
    if not raw:
        return None
    text = _decode_body(raw)
    if not text:
        return None
    if raw == html_data:
        text = _strip_html(text)
    return text.strip() or None


def _decode_body(data: str) -> str:
    try:
        padded = data + "=" * (-len(data) % 4)
        decoded = base64.urlsafe_b64decode(padded.encode("utf-8"))
        return decoded.decode("utf-8", errors="replace")
    except Exception:
        return ""


def _strip_html(value: str) -> str:
    cleaned = re.sub(r"(?i)<br\\s*/?>", "\n", value)
    cleaned = re.sub(r"(?i)</p>", "\n", cleaned)
    cleaned = re.sub(r"<[^>]+>", "", cleaned)
    cleaned = html.unescape(cleaned)
    return cleaned


def _is_work_sender(from_email: str | None, work_domain: str) -> bool:
    if not from_email or not work_domain:
        return False
    domain = from_email.split("@")[-1].lower()
    work_domain = work_domain.lower()
    return domain == work_domain or domain.endswith(f".{work_domain}")


def _clamp(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[: max(0, limit - 3)].rstrip() + "..."


def _parse_bool(value: str | None) -> bool:
    return bool(value) and value.strip().lower() in {"1", "true", "yes", "on"}


def _parse_int(value: str | None, default: int) -> int:
    if value and value.strip().isdigit():
        return int(value)
    return default


def _expand_path(path: str) -> str:
    return os.path.expanduser(path)
