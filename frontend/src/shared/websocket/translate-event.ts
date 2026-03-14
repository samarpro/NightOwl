import { eventSchema, type GatewayEventDto } from "shared/api/contracts";

export function translateGatewayEvent(raw: unknown): GatewayEventDto {
  return eventSchema.parse(raw);
}
