import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { DeliverableContent } from "@/components/workspace/deliverable-view";

afterEach(cleanup);

describe("DeliverableContent", () => {
  it("renders a heading as a heading element rather than as literal '##'", () => {
    render(<DeliverableContent content="## Positioning" />);

    expect(screen.getByRole("heading", { name: "Positioning" })).toBeDefined();
    expect(screen.queryByText(/##/)).toBeNull();
  });

  it("renders emphasis, lists, quotes, links and code as elements", () => {
    const { container } = render(
      <DeliverableContent
        content={[
          "**Revenue** and *reach*.",
          "",
          "- First channel",
          "- Second channel",
          "",
          "> The owner decides at the gate.",
          "",
          "[The plan](https://example.com/plan) and `spend_cap`.",
        ].join("\n")}
      />,
    );

    expect(container.querySelector("strong")?.textContent).toBe("Revenue");
    expect(container.querySelector("em")?.textContent).toBe("reach");
    expect(container.querySelectorAll("ul li")).toHaveLength(2);
    expect(container.querySelector("blockquote")).not.toBeNull();
    expect(container.querySelector("a")?.getAttribute("href")).toBe(
      "https://example.com/plan",
    );
    expect(container.querySelector("code")?.textContent).toBe("spend_cap");
    expect(container.textContent).not.toContain("**");
  });

  it("renders a GitHub-flavoured table as a table", () => {
    const { container } = render(
      <DeliverableContent
        content={[
          "| Channel | Spend |",
          "| --- | --- |",
          "| Meta | 60% |",
        ].join("\n")}
      />,
    );

    expect(container.querySelector("table")).not.toBeNull();
    expect(container.querySelectorAll("tbody tr")).toHaveLength(1);
    expect(container.textContent).not.toContain("|");
  });

  it("does not evaluate raw HTML embedded in model-written markdown", () => {
    const { container } = render(
      <DeliverableContent content={"<img src=x onerror=alert(1)>\n\nAfter."} />,
    );

    expect(container.querySelector("img")).toBeNull();
    expect(container.textContent).toContain("After.");
  });

  it("does not leak the renderer's internal node prop into the markup", () => {
    const { container } = render(
      <DeliverableContent content={"## Heading\n\nA **paragraph**."} />,
    );

    expect(container.querySelector("[node]")).toBeNull();
  });
});
