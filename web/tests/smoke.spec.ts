import { expect, test } from "@playwright/test";

const NAV_ROUTES: Array<{ label: string; path: string }> = [
  { label: "Campaigns", path: "/campaigns" },
  { label: "Calendar", path: "/calendar" },
  { label: "Brand", path: "/brand" },
  { label: "Performance", path: "/performance" },
  { label: "Home", path: "/" },
];

test("nav rail reaches every primary route and marks it active", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page.locator("aside").getByText("Marketing OS")).toBeVisible();

  for (const { label, path } of NAV_ROUTES) {
    const link = page.getByRole("link", { name: label });
    await link.click();
    await expect(page).toHaveURL(path);
    await expect(link).toHaveAttribute("aria-current", "page");
  }
});

test("all routes resolve without a 404", async ({ page }) => {
  const paths = [
    "/",
    "/campaigns",
    "/campaigns/fernway-refill-launch",
    "/campaigns/new",
    "/calendar",
    "/brand",
    "/performance",
    "/onboarding",
  ];
  for (const path of paths) {
    const response = await page.goto(path);
    expect(response, `no response for ${path}`).not.toBeNull();
    expect(response!.status(), `status for ${path}`).toBe(200);
  }
});

test("workspace route highlights the Campaigns nav item", async ({ page }) => {
  await page.goto("/campaigns/fernway-refill-launch");
  await expect(
    page.locator("aside").getByRole("link", { name: "Campaigns" }),
  ).toHaveAttribute("aria-current", "page");
});

test("below the mobile breakpoint the nav collapses into a drawer", async ({
  page,
}) => {
  await page.setViewportSize({ width: 375, height: 720 });
  await page.goto("/");
  await expect(page.getByRole("link", { name: "Campaigns" })).toBeHidden();

  await page.getByRole("button", { name: "Open navigation" }).click();
  await page.getByRole("link", { name: "Campaigns" }).click();
  await expect(page).toHaveURL("/campaigns");

  const overflowX = await page.evaluate(
    () => document.documentElement.scrollWidth > window.innerWidth,
  );
  expect(overflowX).toBe(false);
});
