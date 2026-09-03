import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";

import { STRATEGY_STAGE_INDEX, type AiAction } from "@/lib/mock-data";
import type { Questionnaire } from "@/lib/engine";

export type CalendarMode = "calendar" | "list" | "campaign";
export type RightTab = "evidence" | "comments";
export type AiActionKey = AiAction["key"];

export interface DemoState {
  stage: number;
  approved: boolean;
  reopened: boolean;
  staleCleared: boolean;
  calMode: CalendarMode;
  calSelIdx: number;
  brandIdx: number;
  aiKey: AiActionKey | null;
  rightTab: RightTab;
  questionnaire: Questionnaire | null;
  onboarding: Record<string, string> | null;
  setStage: (stage: number) => void;
  approve: () => void;
  undoApprove: () => void;
  reopen: () => void;
  rerunStale: () => void;
  setCalMode: (mode: CalendarMode) => void;
  setCalSelIdx: (index: number) => void;
  setBrandIdx: (index: number) => void;
  toggleAiKey: (key: AiActionKey) => void;
  setRightTab: (tab: RightTab) => void;
  completeOnboarding: (
    questionnaire: Questionnaire,
    answers: Record<string, string>,
  ) => void;
}

export const useDemoStore = create<DemoState>()(
  persist(
    (set) => ({
      stage: STRATEGY_STAGE_INDEX,
      approved: false,
      reopened: false,
      staleCleared: false,
      calMode: "calendar",
      calSelIdx: 0,
      brandIdx: 0,
      aiKey: null,
      rightTab: "evidence",
      questionnaire: null,
      onboarding: null,
      setStage: (stage) => set({ stage }),
      approve: () => set({ approved: true, reopened: false }),
      undoApprove: () => set({ approved: false }),
      reopen: () =>
        set({
          reopened: true,
          staleCleared: false,
          stage: STRATEGY_STAGE_INDEX,
        }),
      rerunStale: () => set({ staleCleared: true }),
      setCalMode: (calMode) => set({ calMode }),
      setCalSelIdx: (calSelIdx) => set({ calSelIdx }),
      setBrandIdx: (brandIdx) => set({ brandIdx }),
      toggleAiKey: (key) =>
        set((state) => ({ aiKey: state.aiKey === key ? null : key })),
      setRightTab: (rightTab) => set({ rightTab }),
      completeOnboarding: (questionnaire, onboarding) =>
        set({ questionnaire, onboarding }),
    }),
    {
      name: "marketing-os-demo",
      storage: createJSONStorage(() => sessionStorage),
      skipHydration: true,
    },
  ),
);
