import type { SessionNode, SessionTreeNode } from "entities/session/model/types";

export function buildSessionTree(sessions: SessionNode[]) {
  const byId = new Map<string, SessionTreeNode>();
  const roots: SessionTreeNode[] = [];

  sessions.forEach((session) => {
    byId.set(session.id, { ...session, children: [] });
  });

  byId.forEach((session) => {
    if (!session.parentId) {
      roots.push(session);
      return;
    }

    const parent = byId.get(session.parentId);
    if (parent) {
      parent.children.push(session);
    } else {
      roots.push(session);
    }
  });

  return roots;
}
