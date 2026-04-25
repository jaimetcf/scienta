from __future__ import annotations

import uuid
from collections.abc import Mapping
from typing import Any

from psycopg import IntegrityError
from psycopg.rows import dict_row
from psycopg.types.json import Json

from reflex_ui.data import auth_crypto


def _normalize_email(email: str) -> str:
    return email.strip().lower()


async def insert_user(
    pool, email: str, password: str, display_name: str | None
) -> uuid.UUID:
    email_n = _normalize_email(email)
    ph = auth_crypto.hash_password(password)
    async with pool.connection() as conn:
        async with conn.transaction():
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO users (email, display_name, password_hash)
                    VALUES (%s, %s, %s)
                    RETURNING id
                    """,
                    (email_n, display_name, ph),
                )
                row = await cur.fetchone()
    if not row:
        raise RuntimeError("User insert did not return id")
    return row[0]


async def insert_user_safe(
    pool, email: str, password: str, display_name: str | None
) -> uuid.UUID | None:
    try:
        return await insert_user(pool, email, password, display_name)
    except IntegrityError:
        return None


async def fetch_user_by_email(pool, email: str) -> dict[str, Any] | None:
    email_n = _normalize_email(email)
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                """
                SELECT id, email, display_name, password_hash, created_at, updated_at
                FROM users
                WHERE email = %s
                """,
                (email_n,),
            )
            row = await cur.fetchone()
            return dict(row) if row else None


async def fetch_user_by_id(pool, user_id: uuid.UUID) -> dict[str, Any] | None:
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                """
                SELECT id, email, display_name, password_hash, created_at, updated_at
                FROM users
                WHERE id = %s
                """,
                (user_id,),
            )
            row = await cur.fetchone()
            return dict(row) if row else None


async def authenticate_user(pool, email: str, password: str) -> uuid.UUID | None:
    row = await fetch_user_by_email(pool, email)
    if not row:
        return None
    if not auth_crypto.verify_password(password, row["password_hash"]):
        return None
    return row["id"]


async def count_chat_sessions(pool, user_id: uuid.UUID) -> int:
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT COUNT(*)::int
                FROM chat_sessions
                WHERE user_id = %s AND archived_at IS NULL
                """,
                (user_id,),
            )
            row = await cur.fetchone()
            return int(row[0]) if row else 0


async def list_chat_sessions(
    pool, user_id: uuid.UUID, *, limit: int, offset: int
) -> list[dict[str, Any]]:
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                """
                SELECT id, title, created_at, updated_at
                FROM chat_sessions
                WHERE user_id = %s AND archived_at IS NULL
                ORDER BY updated_at DESC
                LIMIT %s OFFSET %s
                """,
                (user_id, limit, offset),
            )
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def list_all_chat_sessions(
    pool, user_id: uuid.UUID
) -> list[dict[str, Any]]:
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                """
                SELECT id, title, created_at, updated_at
                FROM chat_sessions
                WHERE user_id = %s AND archived_at IS NULL
                ORDER BY updated_at DESC
                """,
                (user_id,),
            )
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def create_chat_session(
    pool, user_id: uuid.UUID, title: str = "New Chat"
) -> uuid.UUID:
    async with pool.connection() as conn:
        async with conn.transaction():
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO chat_sessions (user_id, title)
                    VALUES (%s, %s)
                    RETURNING id
                    """,
                    (user_id, title),
                )
                row = await cur.fetchone()
    if not row:
        raise RuntimeError("Session insert did not return id")
    return row[0]


async def update_chat_session_title(
    pool, user_id: uuid.UUID, session_id: uuid.UUID, title: str
) -> bool:
    t = (title or "").strip()
    if not t:
        return False
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                UPDATE chat_sessions
                SET title = %s
                WHERE id = %s AND user_id = %s AND archived_at IS NULL
                """,
                (t, session_id, user_id),
            )
            return cur.rowcount > 0


async def assert_session_owned(
    pool, user_id: uuid.UUID, session_id: uuid.UUID
) -> bool:
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT 1
                FROM chat_sessions
                WHERE id = %s AND user_id = %s AND archived_at IS NULL
                """,
                (session_id, user_id),
            )
            return await cur.fetchone() is not None


async def delete_chat_session(pool, user_id: uuid.UUID, session_id: uuid.UUID) -> bool:
    async with pool.connection() as conn:
        async with conn.transaction():
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    DELETE FROM chat_sessions
                    WHERE id = %s AND user_id = %s
                    """,
                    (session_id, user_id),
                )
                deleted = cur.rowcount
    return deleted > 0


async def list_messages(
    pool, user_id: uuid.UUID, session_id: uuid.UUID
) -> list[dict[str, Any]]:
    if not await assert_session_owned(pool, user_id, session_id):
        return []
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                """
                SELECT id, session_id, role, content, model, token_usage_json,
                       sequence_no, created_at
                FROM chat_messages
                WHERE session_id = %s
                ORDER BY sequence_no ASC, created_at ASC
                """,
                (session_id,),
            )
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def insert_message(
    pool,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    *,
    role: str,
    content: str,
    model: str | None = None,
    token_usage: Mapping[str, Any] | None = None,
) -> uuid.UUID | None:
    async with pool.connection() as conn:
        async with conn.transaction():
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT 1
                    FROM chat_sessions
                    WHERE id = %s AND user_id = %s AND archived_at IS NULL
                    FOR UPDATE
                    """,
                    (session_id, user_id),
                )
                if await cur.fetchone() is None:
                    return None
                usage = Json(dict(token_usage)) if token_usage is not None else None
                await cur.execute(
                    """
                    INSERT INTO chat_messages (
                        session_id, role, content, model, token_usage_json, sequence_no
                    )
                    VALUES (
                        %s, %s, %s, %s, %s,
                        (SELECT COALESCE(MAX(sequence_no), 0) + 1
                         FROM chat_messages WHERE session_id = %s)
                    )
                    RETURNING id
                    """,
                    (session_id, role, content, model, usage, session_id),
                )
                row = await cur.fetchone()
                await cur.execute(
                    """
                    UPDATE chat_sessions
                    SET updated_at = NOW()
                    WHERE id = %s
                    """,
                    (session_id,),
                )
    return row[0] if row else None
