import { expect, test } from "@playwright/test";

const FRONTEND_BASE_URL = process.env.PLAYWRIGHT_TEST_BASE_URL ?? "http://localhost:5173";

/**
 * Azure OpenAI E2E tests against a live backend.
 *
 * Verifies that:
 * 1. The model dropdown shows a comprehensive list including GPT-5.x and Codex
 * 2. The "Accor 3" project can be selected
 * 3. A chat message gets a real response from the LLM
 *
 * These tests require both the backend and frontend to be running.
 */

test.describe("Azure OpenAI E2E", () => {
  test.setTimeout(120_000);

  test("model dropdown lists GPT-5.3, GPT-5.4, and Codex models from live backend", async ({
    page,
  }) => {
    // Navigate to app root and wait for it to load
    await page.goto(`${FRONTEND_BASE_URL}/`);
    await page.waitForLoadState("networkidle");

    // Wait for the provider selector to be visible
    const providerSelect = page.locator('select[aria-label="LLM Provider"]');
    await expect(providerSelect).toBeVisible({ timeout: 15_000 });

    // Select Azure provider if not already selected
    const currentProvider = await providerSelect.inputValue();
    if (currentProvider !== "azure") {
      await providerSelect.selectOption("azure");
      // Wait for model list to load after provider switch
      await page.waitForTimeout(2_000);
    }

    // Wait for the model selector to be visible and populated
    const modelSelect = page.locator('select[aria-label="LLM Model"]');
    await expect(modelSelect).toBeVisible({ timeout: 10_000 });

    // Wait for models to load (more than just the refresh option)
    await expect(async () => {
      const optionCount = await modelSelect.locator("option:not([disabled])").count();
      expect(optionCount).toBeGreaterThan(3);
    }).toPass({ timeout: 15_000 });

    // Collect all option values
    const options = await modelSelect.locator("option").allTextContents();
    const values = await modelSelect.locator("option").evaluateAll(
      (opts) => opts.map((o) => (o as HTMLOptionElement).value),
    );
    const modelIds = values.filter((v) => v && v !== "__refresh__");

    // Log for debugging
    console.log(`Found ${modelIds.length} models:`, modelIds.join(", "));

    // Verify GPT-5.3 models are present
    const has53Chat = modelIds.some((id) => id.includes("5.3-chat") || id.includes("5.3"));
    const has53Codex = modelIds.some((id) => id.includes("5.3-codex"));
    expect(has53Chat || has53Codex).toBe(true);

    // Verify GPT-5.4 models are present
    const has54 = modelIds.some((id) => id.includes("5.4"));
    expect(has54).toBe(true);

    // Verify Codex models are present
    const hasCodex = modelIds.some((id) => id.includes("codex"));
    expect(hasCodex).toBe(true);

    // Verify the deployed model (aaadp) is in the list
    const hasDeployment = modelIds.some((id) => id === "aaadp");
    expect(hasDeployment).toBe(true);

    // Verify minimum model count (should be comprehensive)
    expect(modelIds.length).toBeGreaterThan(10);
  });

  test("chat with Accor 3 project using Azure deployment", async ({
    page,
  }) => {
    const ACCOR3_ID = "01501cd6-3b99-4d33-b638-9024e3a4a1bc";

    // First, set Azure provider + aaadp model via API
    await page.request.put("http://localhost:8000/api/settings/llm-selection", {
      data: { provider_id: "azure", model_id: "aaadp" },
    });

    // Navigate directly to the Accor 3 project page
    await page.goto(`${FRONTEND_BASE_URL}/project/${ACCOR3_ID}`);
    await page.waitForLoadState("networkidle");

    // The chat is in the right sidebar; wait for the chat input
    const chatInput = page.locator(
      'input[placeholder*="Type your message"]',
    );
    await expect(chatInput).toBeVisible({ timeout: 20_000 });

    // Type the prompt
    await chatInput.fill("Give me the NFR based on the inputs");

    // Click the Send button
    const sendButton = page.locator('button:has-text("Send")');
    await expect(sendButton).toBeEnabled({ timeout: 5_000 });
    await sendButton.click();

    // Wait for the response: after sending, new message elements should appear
    // The chat area should contain a response longer than the original prompt
    await expect(async () => {
      const allText = await page
        .locator('[class*="prose"], [class*="message"], [class*="chat"]')
        .allTextContents();
      const combined = allText.join(" ");
      // Response should be longer than just the user prompt
      expect(combined.length).toBeGreaterThan(80);
    }).toPass({ timeout: 90_000 });

    console.log("Chat response received successfully");
  });
});
