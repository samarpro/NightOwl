import { eventSchema, type GatewayEventDto } from "shared/api/contracts";

export function translateGatewayEvent(raw: unknown): GatewayEventDto | null {
  const normalized = normalizeGatewayEvent(raw);
  const result = eventSchema.safeParse(normalized);
  return result.success ? result.data : null;
}

function normalizeGatewayEvent(raw: unknown) {
  if (!raw || typeof raw !== "object") {
    return raw;
  }

  const event = raw as Record<string, unknown>;

  return {
    ...event,
    eventId: typeof event.eventId === "string" ? event.eventId : event.event_id,
    eventType:
      typeof event.eventType === "string"
        ? normalizeEventType(event.eventType)
        : normalizeEventType(event.event_type),
    occurredAt: typeof event.occurredAt === "string" ? event.occurredAt : event.occurred_at
  };
}

function normalizeEventType(value: unknown) {
  if (typeof value !== "string") {
    return value;
  }

  return value === "intent.update" ? "intent.updated" : value;
}
