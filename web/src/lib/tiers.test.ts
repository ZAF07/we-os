import { describe, expect, it } from "vitest";

import {
  launchHref,
  signUpHref,
  tierFromParam,
  TIERS,
  welcomeHref,
} from "@/lib/tiers";

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

describe("tierFromParam", () => {
  it("reads the tier a lowercase query parameter names", () => {
    expect(tierFromParam("command")?.name).toBe("Command");
  });

  it("is forgiving about case, since a person may type the address", () => {
    expect(tierFromParam("Strategist")?.name).toBe("Strategist");
  });

  it("takes the first value when the parameter was repeated", () => {
    expect(tierFromParam(["operator", "command"])?.name).toBe("Operator");
  });

  it("names no tier for an unknown, empty or absent parameter", () => {
    expect(tierFromParam("platinum")).toBeNull();
    expect(tierFromParam("")).toBeNull();
    expect(tierFromParam(undefined)).toBeNull();
  });
});

describe("welcomeHref", () => {
  it("carries the tier to Welcome when there is one", () => {
    expect(welcomeHref(TIERS[2])).toBe("/welcome?tier=command");
  });

  it("is bare Welcome when no tier was chosen, which sends the person to choose", () => {
    expect(welcomeHref(null)).toBe("/welcome");
  });
});

describe("launchHref", () => {
  it("sends a visitor to sign-up with the tier remembered", () => {
    expect(launchHref(TIERS[1], { signedIn: false })).toBe(
      "/sign-up?tier=strategist",
    );
  });

  it("sends a signed-in person to Welcome with the tier, not to a sign-up form", () => {
    expect(launchHref(TIERS[1], { signedIn: true })).toBe(
      "/welcome?tier=strategist",
    );
  });
});
