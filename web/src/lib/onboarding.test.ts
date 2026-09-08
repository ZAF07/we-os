import { describe, expect, it } from "vitest";

import { seedAnswers, toAnswerPayload } from "@/lib/onboarding";

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

describe("seedAnswers", () => {
  it("takes the stored answers when nothing has been typed yet", () => {
    const seeded = seedAnswers({}, [
      { question_id: "q_business_name", answer: "Acme Coffee" },
    ]);

    expect(seeded).toEqual({ q_business_name: "Acme Coffee" });
  });

  it("keeps what the business has typed over a later-arriving load", () => {
    const seeded = seedAnswers({ q_business_name: "Peakline Roasters" }, [
      { question_id: "q_business_name", answer: "Acme Coffee" },
    ]);

    expect(seeded).toEqual({ q_business_name: "Peakline Roasters" });
  });

  it("still fills in a question the business has not touched", () => {
    const seeded = seedAnswers({ q_business_name: "Peakline Roasters" }, [
      { question_id: "q_business_name", answer: "Acme Coffee" },
      { question_id: "q_geography", answer: "Singapore" },
    ]);

    expect(seeded).toEqual({
      q_business_name: "Peakline Roasters",
      q_geography: "Singapore",
    });
  });
});
