import { randomUUID } from "node:crypto";
import { NextResponse } from "next/server";
import {
  assertSessionOwned,
  createChatSession,
  insertMessage,
  listMessages,
  updateChatSessionTitle,
} from "@/lib/repository";
import { currentUserIdFromCookie } from "@/lib/server-auth";
import {
  LLM_MODEL_CHOICES,
  requestAssistantReply,
  summarizeSessionTitle,
  type ApiMessage,
} from "@/lib/webhooks";
import { formatMessageTimePtBr } from "@/lib/formatting";

function nowIso() {
  return new Date().toISOString();
}

export async function POST(request: Request) {
  const body = await request.json().catch(() => ({}));
  const question = String(body?.question ?? "").trim();
  const modelInput = String(body?.model ?? "");
  const model = LLM_MODEL_CHOICES.includes(modelInput as (typeof LLM_MODEL_CHOICES)[number])
    ? modelInput
    : LLM_MODEL_CHOICES[0];
  const providedSessionId = String(body?.sessionId ?? "").trim();
  const userId = await currentUserIdFromCookie();

  if (!question) {
    return NextResponse.json({ error: "Question is required." }, { status: 400 });
  }
  if (!userId) {
    return NextResponse.json({ error: "You must be signed in." }, { status: 401 });
  }

  let sessionId = providedSessionId;
  if (!sessionId || !(await assertSessionOwned(userId, sessionId))) {
    sessionId = await createChatSession(userId);
  }

  const existing = await listMessages(userId, sessionId);
  const isFirstMessage = existing.length === 0;

  await insertMessage({
    userId,
    sessionId,
    role: "user",
    content: question,
    model,
    tokenUsage: null,
  });

  if (isFirstMessage) {
    void summarizeSessionTitle(question).then(async (title) => {
      if (!title) {
        return;
      }
      await updateChatSessionTitle(userId, sessionId, title);
    });
  }

  const stored = await listMessages(userId, sessionId);
  const messagesForApi: ApiMessage[] = stored
    .filter((m) => m.role === "user" || m.role === "assistant")
    .filter((m) => !(m.role === "assistant" && !m.content.trim()))
    .map((m) => ({ role: m.role, content: m.content }));

  if (!messagesForApi.length || messagesForApi[messagesForApi.length - 1]?.content !== question) {
    messagesForApi.push({ role: "user", content: question });
  }

  let assistantText = "";
  try {
    assistantText = await requestAssistantReply(messagesForApi, model);
  } catch (error) {
    const now = nowIso();
    const message = `Error calling workflow webhook: ${
      error instanceof Error ? error.message : String(error)
    }`;
    await insertMessage({
      userId,
      sessionId,
      role: "assistant",
      content: message,
      model,
      tokenUsage: null,
    });
    return NextResponse.json({
      sessionId,
      assistant: {
        id: `assistant-error-${randomUUID()}`,
        role: "assistant",
        content: message,
        created_at: now,
        time_display: formatMessageTimePtBr(now),
      },
      messages: await listMessages(userId, sessionId),
    });
  }

  await insertMessage({
    userId,
    sessionId,
    role: "assistant",
    content: assistantText,
    model,
    tokenUsage: null,
  });
  return NextResponse.json({
    sessionId,
    assistantText,
    messages: await listMessages(userId, sessionId),
  });
}
