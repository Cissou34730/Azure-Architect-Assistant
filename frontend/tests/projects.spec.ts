import { test, expect } from "@playwright/test";

test("projects list renders from API data", async ({ page }) => {
  const projects = [
    { id: "proj-1", name: "Contoso Migration" },
    { id: "proj-2", name: "Fabrikam Landing Zone" },
  ];

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

  await expect(
    page.getByRole("heading", { name: "Architecture Projects" })
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Contoso Migration" })
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Fabrikam Landing Zone" })
  ).toBeVisible();
});
