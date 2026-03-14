import { create } from "zustand";

type SelectionState = {
  selectedSessionId: string | null;
  selectedIntentId: string | null;
  intentSessionId: string | null;
  selectSession: (sessionId: string) => void;
  selectIntent: (intentId: string) => void;
  selectIntentSession: (sessionId: string) => void;
};

export const useSelectionStore = create<SelectionState>((set) => ({
  selectedSessionId: null,
  selectedIntentId: null,
  intentSessionId: null,
  selectSession: (selectedSessionId) => set({ selectedSessionId, intentSessionId: selectedSessionId }),
  selectIntent: (selectedIntentId) => set({ selectedIntentId }),
  selectIntentSession: (intentSessionId) => set({ intentSessionId }),
}));
