import re
from datetime import date, time, timedelta

from ..models import BlockType, WhenBucket

_TIME_TOKEN = r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?"
_TIME_RANGE = re.compile(
    rf"(?:from\s*)?{_TIME_TOKEN}\s*(?:to|till|until|–|-|—)\s*{_TIME_TOKEN}",
    re.IGNORECASE,
)


def parse_task_action(message: str) -> dict | None:
    text = (message or "").strip()
    if not text:
        return None
    lowered = text.lower()
    if not lowered.startswith(("add ", "create ", "capture ")):
        return None
    if "block" in lowered:
        return None
    is_capture = lowered.startswith("capture ")
    mentions_inbox = "inbox" in lowered
    mentions_task = "task" in lowered
    if not is_capture and not mentions_inbox and not mentions_task:
        return None

    title = re.sub(r"^(add|create|capture)\s+", "", text, flags=re.I).strip()
    title = re.sub(r"^(an?\s+)?(inbox|task)\s+", "", title, flags=re.I).strip()
    title = re.sub(r"\b(to|into|in)\s+inbox\b", "", title, flags=re.I).strip()

    when_bucket = None
    bucket_phrases = [
        (r"\btoday\b", WhenBucket.TODAY),
        (r"\bthis week\b", WhenBucket.WEEK),
        (r"\bnext week\b", WhenBucket.WEEK),
        (r"\bthis month\b", WhenBucket.MONTH),
        (r"\bthis quarter\b", WhenBucket.QUARTER),
        (r"\blater\b", WhenBucket.LATER),
        (r"\bsomeday\b", WhenBucket.LATER),
    ]
    if not is_capture and not mentions_inbox:
        for pattern, bucket in bucket_phrases:
            if re.search(pattern, lowered):
                when_bucket = bucket
                title = re.sub(pattern, "", title, flags=re.I).strip()
                break

    if not title:
        return None

    in_inbox = is_capture or mentions_inbox or not when_bucket
    if in_inbox:
        when_bucket = WhenBucket.LATER
    if when_bucket is None:
        when_bucket = WhenBucket.LATER

    return {
        "title": title,
        "in_inbox": in_inbox,
        "when_bucket": when_bucket,
    }


def task_action_reply(title: str, in_inbox: bool, when_bucket: WhenBucket) -> str:
    if in_inbox:
        return (
            f"Captured in your Inbox: \"{title}\". "
            "Want to process it now or keep capturing?"
        )
    bucket_label = when_bucket.value.replace("_", " ")
    return (
        f"Added to {bucket_label.title()}: \"{title}\". "
        "Want to set a block type or duration?"
    )


def parse_one_thing_action(message: str) -> str | None:
    text = (message or "").strip()
    if not text:
        return None
    lowered = text.lower()
    if "one thing" not in lowered:
        return None
    patterns = (
        r"(?:set|make|update)\s+(?:my\s+)?one thing\s+(?:to|as)\s+(.+)",
        r"(?:my\s+)?one thing\s+(?:is|=)\s+(.+)",
    )
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            title = match.group(1).strip().strip(".")
            if title:
                return title
    return None


def _parse_time_token(raw: str, default_ampm: str | None = None) -> time | None:
    match = re.match(r"^(\d{1,2})(?::(\d{2}))?\s*(am|pm)?$", raw.strip(), re.IGNORECASE)
    if not match:
        return None
    hour = int(match.group(1))
    minute = int(match.group(2) or 0)
    if hour > 23 or minute > 59:
        return None
    ampm = (match.group(3) or default_ampm or "").lower()
    if ampm:
        if hour == 12:
            hour = 0 if ampm == "am" else 12
        elif ampm == "pm":
            hour += 12
    else:
        if hour == 12:
            hour = 12
        elif hour <= 7:
            hour += 12
    if hour > 23:
        return None
    return time(hour=hour, minute=minute)


def _block_type_from_text(text: str) -> BlockType:
    lowered = text.lower()
    if "admin" in lowered:
        return BlockType.ADMIN
    if "recovery" in lowered:
        return BlockType.RECOVERY
    if "social" in lowered:
        return BlockType.SOCIAL
    return BlockType.FOCUS


def parse_time_block_action(message: str, reference_date: date | None = None) -> dict | None:
    text = (message or "").strip()
    if not text:
        return None
    lowered = text.lower()
    if not any(token in lowered for token in ("block", "time block", "schedule", "calendar", "book")):
        return None
    match = _TIME_RANGE.search(text)
    if not match:
        return None
    start_raw = f"{match.group(1)}{':' + match.group(2) if match.group(2) else ''}{match.group(3) or ''}"
    end_raw = f"{match.group(4)}{':' + match.group(5) if match.group(5) else ''}{match.group(6) or ''}"
    default_ampm = (match.group(3) or match.group(6) or "").lower() or None
    start_time = _parse_time_token(start_raw, default_ampm)
    end_time = _parse_time_token(end_raw, default_ampm)
    if not start_time or not end_time:
        return None
    if (end_time.hour, end_time.minute) <= (start_time.hour, start_time.minute):
        return None

    block_date = reference_date or date.today()
    if "tomorrow" in lowered:
        block_date = block_date + timedelta(days=1)

    remainder = _TIME_RANGE.sub("", text).strip()
    remainder = re.sub(
        r"^(can you|please|add|create|schedule|book|block|time block|make|put)\b",
        "",
        remainder,
        flags=re.IGNORECASE,
    ).strip()
    title = None
    for pattern in (r"\bfor\s+(.+)$", r"\bto\s+(.+)$"):
        match = re.search(pattern, remainder, flags=re.IGNORECASE)
        if match:
            title = match.group(1).strip().strip(".")
            break
    if not title:
        title = "Focus block"

    return {
        "title": title,
        "date": block_date,
        "start_time": start_time,
        "end_time": end_time,
        "block_type": _block_type_from_text(text),
    }


def one_thing_reply(title: str) -> str:
    return (
        f"Set your One Thing to \"{title}\". "
        "It will show up on Home. Want to set a Frog too?"
    )


def block_action_reply(title: str, block_date: date, start_time: time, end_time: time) -> str:
    date_label = block_date.strftime("%A")
    start_label = start_time.strftime("%I:%M %p").lstrip("0")
    end_label = end_time.strftime("%I:%M %p").lstrip("0")
    return (
        f"Added a block for \"{title}\" on {date_label}, {start_label}-{end_label}. "
        "Want it tied to a task?"
    )
