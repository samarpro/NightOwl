import { skillSaveResponseSchema, skillSummarySchema } from "shared/api/contracts";
import { z } from "zod";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL;
const skillListSchema = z.array(skillSummarySchema);

export async function fetchSkills() {
  const response = await fetch(buildApiUrl("/api/v1/skills/"));
  return parseJsonResponse(response, skillListSchema);
}

export async function saveSkillContent(content: string, source = "settings-editor") {
  const response = await fetch(buildApiUrl("/api/v1/skills/"), {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      content,
      source
    })
  });

  return parseJsonResponse(response, skillSaveResponseSchema);
}

export async function uploadSkillFile(file: File) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(buildApiUrl("/api/v1/skills/upload"), {
    method: "POST",
    body: formData
  });

  return parseJsonResponse(response, skillSaveResponseSchema);
}

async function parseJsonResponse<T>(response: Response, schema: z.ZodSchema<T>) {
  const payload = await response.json().catch(() => null);

  if (!response.ok) {
    const detail =
      payload && typeof payload === "object" && "detail" in payload && typeof payload.detail === "string"
        ? payload.detail
        : `Skills request failed with status ${response.status}`;
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
