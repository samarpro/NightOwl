import { create } from "zustand";

type SelectionState = {
  selectedSessionId: string | null;
  selectedIntentId: string | null;
  selectSession: (sessionId: string) => void;
  selectIntent: (intentId: string) => void;
};

export const useSelectionStore = create<SelectionState>((set) => ({
  selectedSessionId: "sess-main",
  selectedIntentId: "intent-root",
  selectSession: (selectedSessionId) => set({ selectedSessionId }),
  selectIntent: (selectedIntentId) => set({ selectedIntentId })
}));
