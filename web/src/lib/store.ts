import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";

import type { CreatedCampaign } from "@/lib/campaigns";
import { STRATEGY_STAGE_INDEX, type AiAction } from "@/lib/mock-data";
import type { Questionnaire } from "@/lib/engine";

export type CalendarMode = "calendar" | "list" | "campaign";
export type RightTab = "evidence" | "comments";
export type AiActionKey = AiAction["key"];

export interface DemoState {
  stage: number;
  approved: boolean;
  calMode: CalendarMode;
  calSelIdx: number;
  brandIdx: number;
  aiKey: AiActionKey | null;
  rightTab: RightTab;
  questionnaire: Questionnaire | null;
  onboarding: Record<string, string> | null;
  createdCampaigns: CreatedCampaign[];
  setStage: (stage: number) => void;
  approve: () => void;
  undoApprove: () => void;
  setCalMode: (mode: CalendarMode) => void;
  setCalSelIdx: (index: number) => void;
  setBrandIdx: (index: number) => void;
  toggleAiKey: (key: AiActionKey) => void;
  setRightTab: (tab: RightTab) => void;
  completeOnboarding: (
    questionnaire: Questionnaire,
    answers: Record<string, string>,
  ) => void;
  addCampaign: (campaign: CreatedCampaign) => void;
}

export const useDemoStore = create<DemoState>()(
  persist(
    (set) => ({
      stage: STRATEGY_STAGE_INDEX,
      approved: false,
      calMode: "calendar",
      calSelIdx: 0,
      brandIdx: 0,
      aiKey: null,
      rightTab: "evidence",
      questionnaire: null,
      onboarding: null,
      createdCampaigns: [],
      setStage: (stage) => set({ stage }),
      approve: () => set({ approved: true }),
      undoApprove: () => set({ approved: false }),
      setCalMode: (calMode) => set({ calMode }),
      setCalSelIdx: (calSelIdx) => set({ calSelIdx }),
      setBrandIdx: (brandIdx) => set({ brandIdx }),
      toggleAiKey: (key) =>
        set((state) => ({ aiKey: state.aiKey === key ? null : key })),
      setRightTab: (rightTab) => set({ rightTab }),
      completeOnboarding: (questionnaire, onboarding) =>
        set({ questionnaire, onboarding }),
      addCampaign: (campaign) =>
        set((state) => ({
          createdCampaigns: [...state.createdCampaigns, campaign],
          stage: 0,
        })),
    }),
    {
      name: "marketing-os-demo",
      storage: createJSONStorage(() => sessionStorage),
      skipHydration: true,
    },
  ),
);
