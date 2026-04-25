from __future__ import annotations

from datetime import datetime
from typing import Any


def _parse_dt(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and value:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def format_message_time_pt_br(iso: str) -> str:
    """Match Next.js chat `toLocaleTimeString('pt-BR', { hour12: false, ... })`."""
    dt = _parse_dt(iso)
    if dt is None:
        return ""
    return dt.strftime("%H:%M:%S")


def format_session_sidebar_date(iso: str) -> str:
    """Match Next.js session list `toLocaleDateString('en-US', { month: 'short', ... })`."""
    dt = _parse_dt(iso)
    if dt is None:
        return ""
    return dt.strftime("%b %d, %I:%M %p").replace(" 0", " ")


def serialize_session_row(row: dict[str, Any]) -> dict[str, str]:
    updated = row.get("updated_at")
    created = row.get("created_at")
    title = str(row.get("title") or "New Chat")
    title_short = title if len(title) <= 30 else title[:27] + "..."
    return {
        "id": str(row["id"]),
        "title": title,
        "title_short": title_short,
        "updated_at": updated.isoformat() if isinstance(updated, datetime) else "",
        "created_at": created.isoformat() if isinstance(created, datetime) else "",
        "updated_display": format_session_sidebar_date(
            updated.isoformat() if isinstance(updated, datetime) else ""
        ),
    }


def serialize_message_row(row: dict[str, Any]) -> dict[str, str]:
    created = row.get("created_at")
    usage = row.get("token_usage_json")
    usage_s = "" if usage is None else str(usage)
    return {
        "id": str(row["id"]),
        "role": str(row.get("role") or ""),
        "content": str(row.get("content") or ""),
        "model": str(row.get("model") or ""),
        "sequence_no": str(row.get("sequence_no", "")),
        "created_at": created.isoformat() if isinstance(created, datetime) else "",
        "token_usage_json": usage_s,
    }


def thread_message_from_row(row: dict[str, Any]) -> dict[str, str]:
    m = serialize_message_row(row)
    return {
        "id": m["id"],
        "role": m["role"],
        "content": m["content"],
        "created_at": m["created_at"],
        "time_display": format_message_time_pt_br(m["created_at"]),
    }
