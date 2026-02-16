from datetime import datetime, timezone

from app.models import EmailSyncState
from app.utils.gmail import GmailSettings, sync_gmail_inbox


def test_sync_updates_history_checkpoint_when_truncated(monkeypatch, db_session):
    state = EmailSyncState(
        provider="gmail",
        last_history_id="111",
        last_sync_at=datetime.now(timezone.utc),
    )
    db_session.add(state)
    db_session.commit()

    monkeypatch.setattr("app.utils.gmail._gmail_service", lambda settings: object())
    monkeypatch.setattr(
        "app.utils.gmail._history_message_ids",
        lambda service, start_history_id, max_results: ([], "222", True),
    )

    settings = GmailSettings(
        enabled=True,
        client_secrets_path="/tmp/client.json",
        token_path="/tmp/token.json",
        poll_seconds=300,
        max_per_sync=50,
        backfill_days=0,
        work_domain="",
    )

    result = sync_gmail_inbox(db_session, settings)
    assert result["status"] == "ok"
    assert result["truncated"] is True
    assert result["history_updated"] is True

    db_session.refresh(state)
    assert state.last_history_id == "222"
