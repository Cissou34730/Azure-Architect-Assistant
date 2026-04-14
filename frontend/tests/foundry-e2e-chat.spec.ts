import { expect, test, type Page } from "@playwright/test";

const FRONTEND_BASE_URL = process.env.PLAYWRIGHT_TEST_BASE_URL ?? "http://localhost:5173";

async function ensureFoundryProvider(page: Page): Promise<void> {
  const providerSelect = page.locator('select[aria-label="LLM Provider"]');
  await expect(providerSelect).toBeVisible({ timeout: 15_000 });

  if ((await providerSelect.inputValue()) !== "foundry") {
    await providerSelect.selectOption("foundry");
    await page.waitForTimeout(2_000);
  }
}

async function readVisibleModelIds(page: Page): Promise<string[]> {
  const modelSelect = page.locator('select[aria-label="LLM Model"]');
  await expect(modelSelect).toBeVisible({ timeout: 10_000 });

  await expect(async () => {
    const optionCount = await modelSelect.locator("option:not([disabled])").count();
    expect(optionCount).toBeGreaterThan(3);
  }).toPass({ timeout: 15_000 });

  return modelSelect.locator("option").evaluateAll((optionElements) =>
    optionElements
      .filter(
        (optionElement): optionElement is HTMLOptionElement =>
          optionElement instanceof HTMLOptionElement,
      )
      .map((optionElement) => optionElement.value)
      .filter((optionValue) => optionValue !== "" && optionValue !== "__refresh__"),
  );
}

test("Azure AI Foundry dropdown lists GPT-5.3, GPT-5.4, and Codex models from the live backend", async ({
  page,
}) => {
  test.setTimeout(120_000);

  await page.goto(`${FRONTEND_BASE_URL}/`);
  await page.waitForLoadState("networkidle");
  await ensureFoundryProvider(page);

  const modelIds = await readVisibleModelIds(page);
  console.log(`Found ${modelIds.length} models:`, modelIds.join(", "));

  expect(modelIds.some((modelId) => modelId.includes("5.3-chat") || modelId.includes("5.3"))).toBe(true);
  expect(modelIds.some((modelId) => modelId.includes("5.3-codex"))).toBe(true);
  expect(modelIds.some((modelId) => modelId.includes("5.4"))).toBe(true);
  expect(modelIds.some((modelId) => modelId.includes("codex"))).toBe(true);
  expect(modelIds).toContain("aaadp");
  expect(modelIds.length).toBeGreaterThan(10);
});

test("chat with Accor 3 project using the Foundry deployment", async ({ page }) => {
  test.setTimeout(120_000);

  const accorProjectId = "01501cd6-3b99-4d33-b638-9024e3a4a1bc";
  await page.request.put("http://localhost:8000/api/settings/llm-selection", {
    data: { provider_id: "foundry", model_id: "aaadp" },
  });

  await page.goto(`${FRONTEND_BASE_URL}/project/${accorProjectId}`);
  await page.waitForLoadState("networkidle");

  const chatInput = page.locator('input[placeholder*="Type your message"]');
  await expect(chatInput).toBeVisible({ timeout: 20_000 });
  await chatInput.fill("Give me the NFR based on the inputs");

  const sendButton = page.locator('button:has-text("Send")');
  await expect(sendButton).toBeEnabled({ timeout: 5_000 });
  await sendButton.click();

  await expect(async () => {
    const allText = await page
      .locator('[class*="prose"], [class*="message"], [class*="chat"]')
      .allTextContents();
    expect(allText.join(" ").length).toBeGreaterThan(80);
  }).toPass({ timeout: 90_000 });
});
