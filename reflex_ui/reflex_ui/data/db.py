from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from psycopg_pool import AsyncConnectionPool

_pool: AsyncConnectionPool | None = None

# Same placeholder as postgres/init/002_users_password_hash.sql (not a real user password).
_PLACEHOLDER_PASSWORD_HASH = (
    "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW"
)


async def _ensure_users_password_hash_column(pool: "AsyncConnectionPool") -> None:
    """Align older DB volumes with current schema (initdb scripts do not re-run)."""
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_name = 'users'
                )
                """
            )
            row = await cur.fetchone()
            if not row or not row[0]:
                return
            await cur.execute(
                """
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'users'
                  AND column_name = 'password_hash'
                """
            )
            if await cur.fetchone() is not None:
                return
        async with conn.transaction():
            async with conn.cursor() as cur:
                await cur.execute(
                    "ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash TEXT"
                )
                await cur.execute(
                    """
                    UPDATE users
                    SET password_hash = %s
                    WHERE password_hash IS NULL
                    """,
                    (_PLACEHOLDER_PASSWORD_HASH,),
                )
                await cur.execute(
                    "ALTER TABLE users ALTER COLUMN password_hash SET NOT NULL"
                )


def database_url() -> str:
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not set. Example: "
            "postgresql://scienta_user:scienta_password@postgres:5432/scienta"
        )
    return url


async def get_pool() -> AsyncConnectionPool:
    global _pool
    if _pool is not None:
        return _pool
    from psycopg_pool import AsyncConnectionPool

    _pool = AsyncConnectionPool(
        conninfo=database_url(),
        min_size=1,
        max_size=10,
        open=False,
    )
    await _pool.open()
    await _ensure_users_password_hash_column(_pool)
    return _pool
