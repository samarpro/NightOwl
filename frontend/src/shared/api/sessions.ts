import { toSessionNode } from "entities/session/model/adapters";
import { apiSessionMessageSchema, apiSessionSchema } from "shared/api/contracts";
import { z } from "zod";

const sessionListSchema = z.array(apiSessionSchema);
const sessionMessageListSchema = z.array(apiSessionMessageSchema);
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL;

export async function fetchRootSessions() {
  const response = await fetch(buildApiUrl("/api/v1/sessions/"));
  return parseSessionResponse(response);
}

export async function fetchChildSessions(parentId: string) {
  const query = new URLSearchParams({ parentId });
  const response = await fetch(buildApiUrl(`/api/v1/sessions/?${query.toString()}`));
  return parseSessionResponse(response);
}

export async function fetchSessionMessages(sessionId: string) {
  const response = await fetch(buildApiUrl(`/api/v1/sessions/${sessionId}/messages`));

  if (!response.ok) {
    throw new Error(`Session messages request failed with status ${response.status}`);
  }

  return sessionMessageListSchema.parse(await response.json());
}

async function parseSessionResponse(response: Response) {
  if (!response.ok) {
    throw new Error(`Session request failed with status ${response.status}`);
  }

  const payload = sessionListSchema.parse(await response.json());
  return payload.map((session) => toSessionNode(session));
}

function buildApiUrl(path: string) {
  if (!apiBaseUrl?.trim()) {
    throw new Error("VITE_API_BASE_URL is not configured.");
  }

  return new URL(path, apiBaseUrl).toString();
}
