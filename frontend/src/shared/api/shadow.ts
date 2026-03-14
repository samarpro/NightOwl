import {
  shadowCorrectResponseSchema,
  shadowCreateResponseSchema,
  shadowMessageResponseSchema
} from "shared/api/contracts";
import { z } from "zod";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL;

export async function createShadow(sessionId: string) {
  const response = await fetch(buildApiUrl(`/api/v1/sessions/${sessionId}/shadow`), {
    method: "POST"
  });

  return parseJsonResponse(response, shadowCreateResponseSchema);
}

export async function messageShadow(shadowId: string, message: string) {
  const response = await fetch(buildApiUrl(`/api/v1/shadow/${shadowId}/message`), {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ message })
  });

  return parseJsonResponse(response, shadowMessageResponseSchema);
}

export async function correctShadow(shadowId: string, message: string) {
  const response = await fetch(buildApiUrl(`/api/v1/shadow/${shadowId}/correct`), {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ message })
  });

  return parseJsonResponse(response, shadowCorrectResponseSchema);
}

async function parseJsonResponse<T>(response: Response, schema: z.ZodSchema<T>) {
  const payload = await response.json().catch(() => null);

  if (!response.ok) {
    const detail =
      payload && typeof payload === "object" && "detail" in payload && typeof payload.detail === "string"
        ? payload.detail
        : `Shadow request failed with status ${response.status}`;
    throw new Error(detail);
  }

  return schema.parse(payload);
}

function buildApiUrl(path: string) {
  if (!apiBaseUrl?.trim()) {
    throw new Error("VITE_API_BASE_URL is not configured.");
  }

  return new URL(path, apiBaseUrl).toString();
}
