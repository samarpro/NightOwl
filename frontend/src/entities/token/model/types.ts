export type TokenEntry = {
  id: string;
  sessionId: string;
  intentId: string;
  type: "thinking" | "tool_call" | "tool_result" | "response";
  createdAt: string;
  content: string;
};
