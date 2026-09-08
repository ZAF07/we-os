import { describe, expect, it } from "vitest";

import { toAnswerPayload } from "@/lib/onboarding";

describe("toAnswerPayload", () => {
  it("leaves an unanswered question out of the payload", () => {
    const payload = toAnswerPayload({
      q_business_name: "Peakline Roasters",
      q_geography: "",
      q_languages: "   ",
    });

    expect(payload).toEqual([
      { question_id: "q_business_name", answer: "Peakline Roasters" },
    ]);
  });

  it("trims the answers it does send", () => {
    const payload = toAnswerPayload({ q_business_name: "  Peakline  " });

    expect(payload).toEqual([
      { question_id: "q_business_name", answer: "Peakline" },
    ]);
  });
});
