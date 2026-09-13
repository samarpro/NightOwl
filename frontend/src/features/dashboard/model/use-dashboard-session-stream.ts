import { useEffect, useMemo, useRef, useState } from "react";
import {
  applyDashboardSessionEvent,
  createDashboardSessionStreamStateFromSessions,
  initialDashboardSessionStreamState
} from "features/dashboard/model/session-stream";
import type { SessionNode } from "entities/session/model/types";
import { buildDashboardSubscribeMessage, buildGatewayWebSocketUrl } from "shared/websocket/gateway";
import { translateGatewayEvent } from "shared/websocket/translate-event";

export type DashboardWebSocketStatus = "connecting" | "open" | "closed" | "error";

export function useDashboardSessionStream(
  selectedSessionId: string | null,
  rootSessions: SessionNode[],
  childSessions: SessionNode[],
  descendants: SessionNode[] = [],
) {
  const socketRef = useRef<WebSocket | null>(null);
  const selectedSessionIdRef = useRef<string | null>(selectedSessionId);
  const [state, setState] = useState(initialDashboardSessionStreamState);
  const [status, setStatus] = useState<DashboardWebSocketStatus>("connecting");
  const [error, setError] = useState<Error | null>(null);

  selectedSessionIdRef.current = selectedSessionId;

  useEffect(() => {
    setState(createDashboardSessionStreamStateFromSessions(rootSessions, childSessions, descendants));
  }, [childSessions, descendants, rootSessions]);

  useEffect(() => {
    let isMounted = true;
    let socket: WebSocket;

    try {
      socket = new WebSocket(buildGatewayWebSocketUrl());
    } catch (nextError) {
      setStatus("error");
      setError(nextError instanceof Error ? nextError : new Error("Failed to build WebSocket URL."));
      return;
    }

    socketRef.current = socket;
    setStatus("connecting");

    socket.addEventListener("open", () => {
      if (!isMounted) {
        return;
      }

      setStatus("open");
      setError(null);
      socket.send(JSON.stringify(buildDashboardSubscribeMessage(selectedSessionIdRef.current)));
    });

    socket.addEventListener("message", (message) => {
      if (!isMounted) {
        return;
      }

      const parsed = parseGatewayEvent(message.data);
      if (parsed instanceof Error) {
        setError(parsed);
        return;
      }

      if (!parsed) {
        return;
      }

      if (parsed.eventType === "dashboard.snapshot") {
        return;
      }

      setState((current) =>
        applyDashboardSessionEvent(current, parsed, selectedSessionIdRef.current)
      );
    });

    socket.addEventListener("error", () => {
      if (!isMounted) {
        return;
      }

      setStatus("error");
      setError(new Error("The dashboard websocket connection failed."));
    });

    socket.addEventListener("close", () => {
      if (!isMounted) {
        return;
      }

      setStatus("closed");
    });

    return () => {
      isMounted = false;
      socket.close();
      socketRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (socketRef.current?.readyState !== WebSocket.OPEN) {
      return;
    }

    socketRef.current.send(JSON.stringify(buildDashboardSubscribeMessage(selectedSessionId)));
  }, [selectedSessionId]);

  const websocketLabel = useMemo(() => {
    switch (status) {
      case "open":
        return "WebSocket live";
      case "connecting":
        return "WebSocket connecting";
      case "closed":
        return "WebSocket disconnected";
      case "error":
        return "WebSocket error";
    }
  }, [status]);

  return {
    childSessions: state.childSessions,
    descendants: state.descendants,
    rootSessions: state.rootSessions,
    websocketError: error,
    websocketLabel,
    websocketStatus: status
  };
}

function parseGatewayEvent(raw: string) {
  try {
    const parsed = JSON.parse(raw) as unknown;
    return translateGatewayEvent(parsed);
  } catch (error) {
    return error instanceof Error ? error : new Error("Failed to parse dashboard websocket payload.");
  }
}
