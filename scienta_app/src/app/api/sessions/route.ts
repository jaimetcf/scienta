import { NextResponse } from "next/server";
import { createChatSession, listAllChatSessions } from "@/lib/repository";
import { currentUserIdFromCookie } from "@/lib/server-auth";

export async function GET() {
  const userId = await currentUserIdFromCookie();
  if (!userId) {
    return NextResponse.json({ sessions: [] });
  }
  const sessions = await listAllChatSessions(userId);
  return NextResponse.json({ sessions });
}

export async function POST() {
  const userId = await currentUserIdFromCookie();
  if (!userId) {
    return NextResponse.json({ error: "You must be signed in." }, { status: 401 });
  }
  const sessionId = await createChatSession(userId);
  return NextResponse.json({ sessionId });
}
