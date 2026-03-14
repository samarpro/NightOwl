import { z } from "zod";

const promptsSchema = z.object({
  main: z.string(),
  orchestrator: z.string(),
  leaf: z.string(),
});

const apiBaseUrl = (() => {
  const envUrl = import.meta.env.VITE_API_BASE_URL;
  if (!envUrl?.trim()) {
    throw new Error("VITE_API_BASE_URL is not configured.");
  }
  return envUrl;
})();

export async function fetchPrompts(): Promise<z.infer<typeof promptsSchema>> {
  const response = await fetch(new URL("/api/v1/prompts/", apiBaseUrl).toString());
  if (!response.ok) {
    throw new Error(`Failed to fetch prompts: ${response.status}`);
  }
  return promptsSchema.parse(await response.json());
}

export async function updatePrompts(
  update: Partial<z.infer<typeof promptsSchema>>
): Promise<z.infer<typeof promptsSchema>> {
  const response = await fetch(new URL("/api/v1/prompts/", apiBaseUrl).toString(), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(update),
  });
  if (!response.ok) {
    throw new Error(`Failed to update prompts: ${response.status}`);
  }
  return promptsSchema.parse(await response.json());
}
