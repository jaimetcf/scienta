export function parseDate(value: unknown): Date | null {
  if (value instanceof Date) {
    return value;
  }
  if (typeof value === "string" && value) {
    const d = new Date(value);
    return Number.isNaN(d.getTime()) ? null : d;
  }
  return null;
}

export function formatMessageTimePtBr(iso: string): string {
  const dt = parseDate(iso);
  if (!dt) {
    return "";
  }
  return dt.toLocaleTimeString("pt-BR", {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export function formatSessionSidebarDate(iso: string): string {
  const dt = parseDate(iso);
  if (!dt) {
    return "";
  }
  return dt.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}
