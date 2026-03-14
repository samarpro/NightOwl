import { z } from "zod";

const intentGraphNodeSchema = z.object({
  id: z.string(),
  label: z.string(),
  type: z.string(),
  service: z.string().default(""),
  intent: z.string().default(""),
  summary: z.string().default(""),
  token_start: z.number().default(0),
  token_end: z.number().default(0),
  started_at: z.number().default(0),
  ended_at: z.number().default(0),
});

const intentGraphEdgeSchema = z.object({
  source: z.string(),
  target: z.string(),
  label: z.string(),
});

const intentGraphSchema = z.object({
  nodes: z.array(intentGraphNodeSchema),
  edges: z.array(intentGraphEdgeSchema),
});

const apiBaseUrl = (() => {
  const envUrl = import.meta.env.VITE_API_BASE_URL;
  if (!envUrl?.trim()) {
    throw new Error("VITE_API_BASE_URL is not configured.");
  }
  return envUrl;
})();

export async function fetchIntentGraph(sessionId: string): Promise<z.infer<typeof intentGraphSchema>> {
  const response = await fetch(new URL(`/api/v1/observability/intent-graph/${sessionId}`, apiBaseUrl).toString());
  if (!response.ok) {
    throw new Error(`Failed to fetch intent graph: ${response.status}`);
  }
  return intentGraphSchema.parse(await response.json());
}

const tokenEntrySchema = z.object({
  type: z.string(),
  content: z.string(),
  metadata: z.record(z.unknown()).default({}),
  timestamp: z.number(),
});

export type TokenEntry = z.infer<typeof tokenEntrySchema>;

export async function fetchTokenRange(
  sessionId: string,
  start: number,
  end: number,
): Promise<TokenEntry[]> {
  const url = new URL(`/api/v1/observability/tokens/${sessionId}/range`, apiBaseUrl);
  url.searchParams.set("start", String(start));
  url.searchParams.set("end", String(end));
  const response = await fetch(url.toString());
  if (!response.ok) {
    throw new Error(`Failed to fetch token range: ${response.status}`);
  }
  return z.array(tokenEntrySchema).parse(await response.json());
}

export async function fetchAllIntentGraphs(): Promise<Record<string, z.infer<typeof intentGraphSchema>>> {
  const response = await fetch(new URL("/api/v1/observability/intent-graphs", apiBaseUrl).toString());
  if (!response.ok) {
    throw new Error(`Failed to fetch intent graphs: ${response.status}`);
  }
  const data = await response.json();
  const result: Record<string, z.infer<typeof intentGraphSchema>> = {};
  for (const [sessionId, graph] of Object.entries(data)) {
    result[sessionId] = intentGraphSchema.parse(graph);
  }
  return result;
}
