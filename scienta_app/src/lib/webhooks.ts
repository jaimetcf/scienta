import { getOptionalEnv } from "@/lib/env";

export const LLM_MODEL_CHOICES = [
  "gpt-5.4",
  "gpt-4o-mini",
  "gpt-4o",
  "gpt-4-turbo",
  "gpt-3.5-turbo",
] as const;

export type ChatRole = "user" | "assistant";

export type ApiMessage = {
  role: ChatRole;
  content: string;
};

const TITLE_SUMMARY_MODEL = "gpt-4o-mini";

export function capSessionTitleWords(text: string, maxWords = 10): string {
  const words = (text || "").replace(/\n/g, " ").split(/\s+/).filter(Boolean);
  return words.slice(0, maxWords).join(" ");
}

export function extractAssistantTextFromWebhook(data: unknown): string {
  if (typeof data === "string") {
    return data.trim();
  }

  if (Array.isArray(data)) {
    for (const item of data) {
      const text = extractAssistantTextFromWebhook(item);
      if (text) {
        return text;
      }
    }
    return "";
  }

  if (data && typeof data === "object") {
    const obj = data as Record<string, unknown>;
    for (const key of ["output", "answer", "response", "content", "message", "text"]) {
      const value = obj[key];
      if (typeof value === "string" && value.trim()) {
        return value.trim();
      }
    }
    for (const key of ["data", "result", "body"]) {
      const text = extractAssistantTextFromWebhook(obj[key]);
      if (text) {
        return text;
      }
    }
  }

  return "";
}

async function postWebhook(url: string, payload: object): Promise<unknown> {
  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }

  const rawText = (await response.text()).trim();
  if (!rawText) {
    return "";
  }
  try {
    return JSON.parse(rawText);
  } catch {
    return rawText;
  }
}

export async function requestAssistantReply(messages: ApiMessage[], model: string): Promise<string> {
  const webhookUrl = getOptionalEnv("N8N_CHAT_WEBHOOK");
  if (!webhookUrl) {
    throw new Error("N8N_CHAT_WEBHOOK is not set.");
  }

  const webhookResponse = await postWebhook(webhookUrl, {
    messages,
    model,
  });
  const assistantText = extractAssistantTextFromWebhook(webhookResponse);
  if (!assistantText) {
    throw new Error("N8N webhook did not return assistant text in the response.");
  }
  return assistantText;
}

export async function summarizeSessionTitle(userMessage: string): Promise<string> {
  const summaryWebhookUrl = getOptionalEnv("N8N_SUMMARY_WEBHOOK");
  if (!summaryWebhookUrl || !userMessage.trim()) {
    return "";
  }
  const webhookResponse = await postWebhook(summaryWebhookUrl, {
    messages: [{ role: "user", content: userMessage.trim() }],
    model: TITLE_SUMMARY_MODEL,
  });
  return capSessionTitleWords(extractAssistantTextFromWebhook(webhookResponse), 10);
}
