import asyncio
import json
import os
import uuid
from datetime import datetime, timezone
from urllib import error as urllib_error
from urllib import request as urllib_request

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


def _extract_assistant_text_from_webhook(data: object) -> str:
    if isinstance(data, str):
        return data.strip()

    if isinstance(data, list):
        for item in data:
            text = _extract_assistant_text_from_webhook(item)
            if text:
                return text
        return ""

    if isinstance(data, dict):
        for key in ("output", "answer", "response", "content", "message", "text"):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        # Common n8n shape where content is nested inside another object.
        for key in ("data", "result", "body"):
            value = data.get(key)
            text = _extract_assistant_text_from_webhook(value)
            if text:
                return text
        return ""

    return ""


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

        assistant_text = ""
        try:
            webhook_url = os.environ.get("N8N_WEBHOOK", "").strip()
            print(f"[scienta] N8N_WEBHOOK={webhook_url}")
            if not webhook_url:
                raise RuntimeError("N8N_WEBHOOK is not set.")

            webhook_messages = list(msgs_for_api)
            expected_last_user_message = {"role": "user", "content": question}
            if not webhook_messages or webhook_messages[-1] != expected_last_user_message:
                webhook_messages.append(expected_last_user_message)

            payload = {
                "messages": webhook_messages,
                "model": model,
            }

            def _call_n8n_webhook() -> object:
                body = json.dumps(payload).encode("utf-8")
                req = urllib_request.Request(
                    webhook_url,
                    data=body,
                    method="POST",
                    headers={"Content-Type": "application/json"},
                )
                with urllib_request.urlopen(req, timeout=120) as response:
                    raw = response.read().decode("utf-8").strip()
                    if not raw:
                        return ""
                    try:
                        return json.loads(raw)
                    except json.JSONDecodeError:
                        return raw

            webhook_response = await asyncio.to_thread(_call_n8n_webhook)
            assistant_text = _extract_assistant_text_from_webhook(webhook_response)
            if not assistant_text:
                raise RuntimeError(
                    "N8N webhook did not return assistant text in the response."
                )

            now = _now_iso()
            async with self:
                self.thread_messages.append(
                    {
                        "id": f"assistant-{uuid.uuid4()}",
                        "role": "assistant",
                        "content": assistant_text,
                        "created_at": now,
                        "time_display": format_message_time_pt_br(now),
                    }
                )
            yield
            yield _scroll_chat_to_bottom()
        except (urllib_error.URLError, urllib_error.HTTPError, RuntimeError) as e:
            now = _now_iso()
            async with self:
                self.thread_messages.append(
                    {
                        "id": f"assistant-error-{uuid.uuid4()}",
                        "role": "assistant",
                        "content": f"Error calling workflow webhook: {e}",
                        "created_at": now,
                        "time_display": format_message_time_pt_br(now),
                    }
                )
            yield
            yield _scroll_chat_to_bottom()
        except Exception as e:
            now = _now_iso()
            async with self:
                self.thread_messages.append(
                    {
                        "id": f"assistant-error-{uuid.uuid4()}",
                        "role": "assistant",
                        "content": f"Unexpected error while getting response: {e}",
                        "created_at": now,
                        "time_display": format_message_time_pt_br(now),
                    }
                )
            yield
            yield _scroll_chat_to_bottom()

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
                self.thread_messages = [thread_message_from_row(r) for r in rows]
            await self.refresh_sessions()
        async with self:
            self.is_loading = False
