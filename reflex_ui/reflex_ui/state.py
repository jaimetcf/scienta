import asyncio
import os
import uuid
from datetime import datetime, timezone

from openai import AsyncOpenAI
import reflex as rx
from reflex.event import EventSpec

from reflex_ui import style
from reflex_ui.chat_data_state import ChatDataState
from reflex_ui.data import auth_crypto, repository
from reflex_ui.data.db import get_pool
from reflex_ui.data.formatting import format_message_time_pt_br, thread_message_from_row

# OpenAI model ids for chat completions (streaming).
LLM_MODEL_CHOICES: list[str] = [
    "gpt-5.4",
    "gpt-4o-mini",
    "gpt-4o",
    "gpt-4-turbo",
    "gpt-3.5-turbo",
]


def _scroll_chat_to_bottom() -> EventSpec:
    sid = style.chat_scroll_area_id
    return rx.call_script(
        "requestAnimationFrame(() => {"
        f"const el = document.getElementById({sid!r});"
        "if (el) { el.scrollTop = el.scrollHeight; }"
        "});"
    )


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


_SESSION_TITLE_SYSTEM_PROMPT = (
    "Your work is to summaraize the user message in a sentence with a maximum of 10 words, "
    "but try to make it as short as possible."
)

_TITLE_SUMMARY_MODEL = "gpt-4o-mini"


def _cap_session_title_words(text: str, max_words: int = 10) -> str:
    words = (text or "").replace("\n", " ").split()
    if not words:
        return ""
    return " ".join(words[:max_words])


class State(ChatDataState):
    question: str
    is_loading: bool = False
    llm_model: str = LLM_MODEL_CHOICES[0]

    @rx.var
    def ask_disabled(self) -> bool:
        return self.is_loading or not self.question.strip()

    @rx.var
    def chat_input_disabled(self) -> bool:
        return self.is_loading

    @rx.var
    def show_typing_indicator(self) -> bool:
        if not self.is_loading:
            return False
        if not self.thread_messages:
            return True
        last = self.thread_messages[-1]
        if last.get("role") != "assistant":
            return True
        return not (last.get("content") or "").strip()

    def set_question(self, value: str):
        self.question = value

    def set_llm_model(self, value: str):
        self.llm_model = value

    def submit_if_enter(self, key: str):
        if key != "Enter" or not self.question.strip() or self.is_loading:
            return
        return State.answer

    def login_submit_if_enter(self, key: str):
        if key != "Enter":
            return
        return State.login_submit

    def register_submit_if_enter(self, key: str):
        if key != "Enter":
            return
        return State.register_submit

    async def _summarize_session_title_task(
        self,
        pool,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        user_message: str,
    ) -> None:
        try:
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key or not user_message.strip():
                return
            client = AsyncOpenAI(api_key=api_key)
            resp = await client.chat.completions.create(
                model=_TITLE_SUMMARY_MODEL,
                messages=[
                    {"role": "system", "content": _SESSION_TITLE_SYSTEM_PROMPT},
                    {"role": "user", "content": user_message.strip()},
                ],
                temperature=0.3,
                max_tokens=64,
            )
            raw = (resp.choices[0].message.content or "").strip()
            title = _cap_session_title_words(raw, 10)
            if not title:
                return
            updated = await repository.update_chat_session_title(
                pool, user_id, session_id, title
            )
            if not updated:
                return
            async with self:
                await self.refresh_sessions()
        except Exception:
            return

    def _messages_for_api(self) -> list[dict[str, str]]:
        out: list[dict[str, str]] = []
        for m in self.thread_messages:
            role = m.get("role") or ""
            if role not in ("user", "assistant"):
                continue
            content = m.get("content") or ""
            if role == "assistant" and not content.strip():
                continue
            out.append({"role": role, "content": content})
        return out

    @rx.event(background=True)
    async def answer(self):
        async with self:
            if self.is_loading:
                return
            question = self.question.strip()
            if not question:
                return
            self.is_loading = True
            model = self.llm_model
            token = self.session_token

        yield

        user_id = auth_crypto.verify_user_token(token) if token else None
        pool = None
        if user_id is not None:
            try:
                pool = await get_pool()
            except RuntimeError:
                user_id = None

        sid_uuid: uuid.UUID | None = None
        if user_id is not None and pool is not None:
            async with self:
                raw_session = (self.current_session_id or "").strip()
            if raw_session:
                try:
                    cand = uuid.UUID(raw_session)
                    if await repository.assert_session_owned(pool, user_id, cand):
                        sid_uuid = cand
                except ValueError:
                    sid_uuid = None
            if sid_uuid is None:
                new_sid = await repository.create_chat_session(pool, user_id)
                async with self:
                    self.current_session_id = str(new_sid)
                sid_uuid = new_sid
            else:
                pass

            rows_before = await repository.list_messages(pool, user_id, sid_uuid)
            is_first_message_in_session = len(rows_before) == 0

            await repository.insert_message(
                pool,
                user_id,
                sid_uuid,
                role="user",
                content=question,
                model=model,
                token_usage=None,
            )
            if is_first_message_in_session:
                asyncio.create_task(
                    self._summarize_session_title_task(
                        pool, user_id, sid_uuid, question
                    )
                )
            rows = await repository.list_messages(pool, user_id, sid_uuid)
            async with self:
                self.thread_messages = [thread_message_from_row(r) for r in rows]
                self.question = ""
        else:
            now = _now_iso()
            async with self:
                self.thread_messages.append(
                    {
                        "id": f"local-{uuid.uuid4()}",
                        "role": "user",
                        "content": question,
                        "created_at": now,
                        "time_display": format_message_time_pt_br(now),
                    }
                )
                self.question = ""

        yield
        yield _scroll_chat_to_bottom()

        async with self:
            msgs_for_api = self._messages_for_api()
        if not msgs_for_api:
            msgs_for_api = [{"role": "user", "content": question}]

        try:
            client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])
            session = await client.chat.completions.create(
                model=model,
                messages=msgs_for_api,
                temperature=0.7,
                stream=True,
            )

            first_assistant_chunk = True
            async for item in session:
                delta = item.choices[0].delta
                if not hasattr(delta, "content"):
                    continue
                if delta.content is None:
                    continue
                chunk = delta.content
                if not chunk:
                    continue
                async with self:
                    if first_assistant_chunk:
                        self.thread_messages.append(
                            {
                                "id": "streaming",
                                "role": "assistant",
                                "content": chunk,
                                "created_at": "",
                                "time_display": "",
                            }
                        )
                        first_assistant_chunk = False
                    else:
                        if not self.thread_messages:
                            continue
                        last = self.thread_messages[-1]
                        if last.get("role") != "assistant":
                            self.thread_messages.append(
                                {
                                    "id": "streaming",
                                    "role": "assistant",
                                    "content": chunk,
                                    "created_at": "",
                                    "time_display": "",
                                }
                            )
                        else:
                            self.thread_messages[-1] = {
                                **last,
                                "content": (last.get("content") or "") + chunk,
                            }
                yield
                yield _scroll_chat_to_bottom()

            assistant_text = ""
            async with self:
                if self.thread_messages:
                    last = self.thread_messages[-1]
                    if last.get("role") == "assistant":
                        assistant_text = last.get("content") or ""

            if (
                user_id is not None
                and pool is not None
                and sid_uuid is not None
                and assistant_text
            ):
                await repository.insert_message(
                    pool,
                    user_id,
                    sid_uuid,
                    role="assistant",
                    content=assistant_text,
                    model=model,
                    token_usage=None,
                )
                rows = await repository.list_messages(pool, user_id, sid_uuid)
                async with self:
                    self.thread_messages = [
                        thread_message_from_row(r) for r in rows
                    ]
                await self.refresh_sessions()
        finally:
            async with self:
                self.is_loading = False
