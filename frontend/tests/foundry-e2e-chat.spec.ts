import { expect, test, type Page } from "@playwright/test";

const FRONTEND_BASE_URL = process.env.PLAYWRIGHT_TEST_BASE_URL ?? "http://localhost:5173";
const BACKEND_BASE_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

interface BackendProvider {
  readonly id: string;
  readonly models: readonly { readonly id: string }[];
}

interface BackendLLMOptionsResponse {
  readonly providers: readonly BackendProvider[];
}

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
          optionElement instanceof HTMLOptionElement && !optionElement.disabled,
      )
      .map((optionElement) => optionElement.value)
      .filter((optionValue) => optionValue !== "" && optionValue !== "__refresh__"),
  );
}

async function fetchFoundryModelIds(page: Page): Promise<string[]> {
  const response = await page.request.get(`${BACKEND_BASE_URL}/api/settings/llm-options?refresh=true`);
  expect(response.ok()).toBe(true);

  const payload = (await response.json()) as BackendLLMOptionsResponse;
  const foundryProvider = payload.providers.find((provider) => provider.id === "foundry");
  expect(foundryProvider).toBeDefined();

  return foundryProvider?.models.map((model) => model.id) ?? [];
}

test("Azure AI Foundry dropdown lists the live Foundry deployments", async ({ page }) => {
  test.setTimeout(120_000);

  await page.goto(`${FRONTEND_BASE_URL}/`);
  await page.waitForLoadState("networkidle");
  await ensureFoundryProvider(page);

  const modelIds = await readVisibleModelIds(page);
  console.log(`Found ${modelIds.length} models:`, modelIds.join(", "));

  expect(modelIds.length).toBeGreaterThanOrEqual(4);
  expect(modelIds).toContain("aaadp");
  expect(modelIds.some((modelId) => modelId.includes("5.3"))).toBe(true);
  expect(modelIds.some((modelId) => modelId.includes("5.4") || modelId.includes("54-"))).toBe(true);
});

test("Azure AI Foundry model selection from the dropdown persists to the backend", async ({ page }) => {
  test.setTimeout(120_000);

  await page.goto(`${FRONTEND_BASE_URL}/`);
  await page.waitForLoadState("networkidle");
  await ensureFoundryProvider(page);

  const backendModelIds = await fetchFoundryModelIds(page);
  const targetModelId = backendModelIds.find((modelId) => modelId !== "aaadp") ?? backendModelIds[0];
  expect(targetModelId).toBeTruthy();

  const modelSelect = page.locator('select[aria-label="LLM Model"]');
  await modelSelect.selectOption(targetModelId);

  await expect(modelSelect).toHaveValue(targetModelId, { timeout: 30_000 });
  await expect(async () => {
    const currentModelResponse = await page.request.get(`${BACKEND_BASE_URL}/api/settings/current-model`);
    expect(currentModelResponse.ok()).toBe(true);
    const payload = (await currentModelResponse.json()) as { readonly model: string };
    expect(payload.model).toBe(targetModelId);
  }).toPass({ timeout: 30_000 });
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
