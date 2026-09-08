import { describe, expect, it } from "vitest";

import { signUpHref, TIERS } from "@/lib/tiers";

describe("TIERS", () => {
  it("offers the three tiers, smallest first", () => {
    expect(TIERS.map((tier) => tier.name)).toEqual([
      "Operator",
      "Strategist",
      "Command",
    ]);
  });

  it("marks Strategist, and only Strategist, as the common choice", () => {
    const highlighted = TIERS.filter((tier) => tier.highlighted);

    expect(highlighted.map((tier) => tier.name)).toEqual(["Strategist"]);
  });
});

describe("signUpHref", () => {
  it("carries the tier to sign-up as a lowercase query parameter", () => {
    expect(TIERS.map(signUpHref)).toEqual([
      "/sign-up?tier=operator",
      "/sign-up?tier=strategist",
      "/sign-up?tier=command",
    ]);
  });
});
