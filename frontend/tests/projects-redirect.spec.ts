import { expect, test } from "@playwright/test";

test("legacy /projects route redirects to the canonical project list", async ({
  page,
}) => {
  const projects = [
    { id: "proj-1", name: "Contoso Migration" },
    { id: "proj-2", name: "Fabrikam Landing Zone" },
  ];

  await page.route("**/api/settings/available-models**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ models: [] }),
    });
  });

  await page.route("**/api/settings/current-model", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(""),
    });
  });

  await page.route("**/api/projects*", async (route) => {
    const request = route.request();
    if (request.method() !== "GET") {
      await route.fulfill({
        status: 405,
        contentType: "application/json",
        body: JSON.stringify({ error: "Method not allowed" }),
      });
      return;
    }

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ projects }),
    });
  });

  await page.goto("/projects");

  await expect
    .poll(() => {
      const currentUrl = new URL(page.url());
      return `${currentUrl.pathname}${currentUrl.search}`;
    })
    .toBe("/project");

  await expect(
    page.getByRole("heading", { name: "Architecture Projects" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Contoso Migration" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Fabrikam Landing Zone" }),
  ).toBeVisible();
});
