import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";

import type { Questionnaire } from "@/lib/engine";

export type CalendarMode = "calendar" | "list" | "campaign";

export interface DemoState {
  approved: boolean;
  calMode: CalendarMode;
  calSelIdx: number;
  brandIdx: number;
  questionnaire: Questionnaire | null;
  onboarding: Record<string, string> | null;
  setCalMode: (mode: CalendarMode) => void;
  setCalSelIdx: (index: number) => void;
  setBrandIdx: (index: number) => void;
  completeOnboarding: (
    questionnaire: Questionnaire,
    answers: Record<string, string>,
  ) => void;
}

/**
 * Client state for the screens still driven by fixtures.
 *
 * The Workspace no longer reads from here: its stage selection, approval and
 * staleness come from the engine, which is the only thing that knows them. What
 * remains belongs to Home, Brand and Calendar, and goes when those screens are
 * wired.
 */
export const useDemoStore = create<DemoState>()(
  persist(
    (set) => ({
      approved: false,
      calMode: "calendar",
      calSelIdx: 0,
      brandIdx: 0,
      questionnaire: null,
      onboarding: null,
      setCalMode: (calMode) => set({ calMode }),
      setCalSelIdx: (calSelIdx) => set({ calSelIdx }),
      setBrandIdx: (brandIdx) => set({ brandIdx }),
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
