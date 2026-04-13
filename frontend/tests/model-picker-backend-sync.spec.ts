import { expect, test } from "@playwright/test";

/**
 * Model picker / backend sync E2E test.
 *
 * Validates that the model dropdown in the navigation bar displays
 * exactly the same models that the live backend reports for the active provider.
 *
 * This test requires both the backend (port 8000) and the frontend dev server
 * to be running.  It does NOT mock any API responses.
 */

const BACKEND_BASE_URL = process.env.BACKEND_URL ?? "http://localhost:8000";
const REFRESH_OPTION_VALUE = "__refresh__";

/** Shape of the raw /api/settings/llm-options response (snake_case, as FastAPI returns it). */
interface BackendModel {
  id: string;
  name: string;
  context_window: number;
  pricing: { input: number; output: number; currency: string } | null;
}

interface BackendProvider {
  id: string;
  name: string;
  status: string;
  status_message: string | null;
  selected: boolean;
  models: BackendModel[];
}

interface BackendLLMOptionsResponse {
  active_provider: string;
  active_model: string;
  providers: BackendProvider[];
}

test.describe("Model picker / backend sync", () => {
  test.setTimeout(60_000);

  test("model dropdown matches the live backend model list for the active provider", async ({
    page,
  }) => {
    // ── Step 1: Load the frontend ───────────────────────────────────────────

    await page.goto("/");

    const modelSelect = page.locator('select[aria-label="LLM Model"]');
    await expect(
      modelSelect,
      "Model picker dropdown is not visible on the page",
    ).toBeVisible({ timeout: 20_000 });

    // Wait for the initial model list to be populated (not just the refresh sentinel).
    // 30s budget: the first backend call may wait up to 5s for the Azure deployments
    // discovery probe before falling back, on top of the normal network round-trip.
    await expect(async () => {
      const enabledOptions = await modelSelect
        .locator("option:not([disabled])")
        .evaluateAll((opts) =>
          opts
            .map((el) => (el as HTMLOptionElement).value)
            .filter((v) => v !== "__refresh__" && v !== ""),
        );
      expect(enabledOptions.length).toBeGreaterThan(0);
    }).toPass({ timeout: 30_000 });

    // ── Step 2: Trigger "Refresh models" so the UI fetches the full list ────
    //
    // The initial load uses refresh=false, which may return only the configured
    // deployment ID. Selecting the "__refresh__" sentinel fires refresh=true on
    // the backend, which queries the provider API for all deployed models.

    await modelSelect.selectOption("__refresh__");

    // Wait for the refresh spinner to disappear — the option text switches back
    // from "Refreshing models..." to "Refresh models" once the fetch is done.
    await expect(
      modelSelect.locator('option[value="__refresh__"]'),
      "Refresh did not complete within timeout",
    ).toHaveText("Refresh models", { timeout: 30_000 });

    // ── Step 3: Fetch the same refreshed data from the backend ─────────────

    const apiResponse = await page.request.get(
      `${BACKEND_BASE_URL}/api/settings/llm-options?refresh=true`,
    );

    expect(
      apiResponse.ok(),
      `Backend /api/settings/llm-options?refresh=true returned HTTP ${apiResponse.status()}`,
    ).toBe(true);

    const data = (await apiResponse.json()) as BackendLLMOptionsResponse;
    const activeProvider = data.providers.find((p) => p.id === data.active_provider);

    expect(
      activeProvider,
      `Active provider "${data.active_provider}" not found in providers list`,
    ).toBeDefined();

    const backendModelIds = (activeProvider!).models.map((m) => m.id);

    console.log(
      `Backend (refreshed): active provider = "${data.active_provider}", ` +
        `${backendModelIds.length} model(s): ${backendModelIds.join(", ")}`,
    );

    if (backendModelIds.length === 0) {
      console.warn(
        `Provider "${data.active_provider}" has 0 models after refresh — ` +
          "skipping UI comparison (environment not fully configured).",
      );
      return;
    }

    // ── Step 4: Extract model IDs that the UI is now showing ───────────────

    const uiModelIds: string[] = await modelSelect
      .locator("option")
      .evaluateAll((opts) =>
        opts
          .filter((el) => !(el as HTMLOptionElement).disabled)
          .map((el) => (el as HTMLOptionElement).value)
          .filter((v) => v !== "" && v !== "__refresh__"),
      );

    console.log(`UI dropdown (refreshed): ${uiModelIds.length} model(s): ${uiModelIds.join(", ")}`);

    // ── Step 5: Assert exact bidirectional match ────────────────────────────

    for (const modelId of backendModelIds) {
      expect(
        uiModelIds,
        `Backend model "${modelId}" is missing from the UI model picker`,
      ).toContain(modelId);
    }

    for (const modelId of uiModelIds) {
      expect(
        backendModelIds,
        `UI model picker shows "${modelId}" but the backend did not return it`,
      ).toContain(modelId);
    }

    expect(
      uiModelIds.length,
      `UI has ${uiModelIds.length} models but backend returned ${backendModelIds.length}`,
    ).toBe(backendModelIds.length);
  });

  test("provider picker only shows providers that the backend knows about", async ({
    page,
  }) => {
    // Fetch the full provider list from the backend
    const apiResponse = await page.request.get(
      `${BACKEND_BASE_URL}/api/settings/llm-options`,
    );
    expect(apiResponse.ok()).toBe(true);

    const data = (await apiResponse.json()) as BackendLLMOptionsResponse;
    const backendProviderIds = data.providers.map((p) => p.id);
    const activeProviderId = data.active_provider;

    console.log(
      `Backend providers: ${backendProviderIds.join(", ")} (active: ${activeProviderId})`,
    );

    await page.goto("/");

    const providerSelect = page.locator('select[aria-label="LLM Provider"]');
    await expect(providerSelect).toBeVisible({ timeout: 20_000 });

    // Wait until the active provider's option is present, so we know the
    // async data has been fetched and the options have been rendered.
    await expect(
      providerSelect.locator(`option[value="${activeProviderId}"]`),
      `Active provider "${activeProviderId}" must appear in the provider picker`,
    ).toBeAttached({ timeout: 15_000 });

    // Collect all provider options rendered by the UI
    const uiProviderIds: string[] = await providerSelect
      .locator("option")
      .evaluateAll((opts) =>
        opts
          .filter((el) => !(el as HTMLOptionElement).disabled)
          .map((el) => (el as HTMLOptionElement).value)
          .filter((v) => v !== ""),
      );

    console.log(`UI providers: ${uiProviderIds.join(", ")}`);

    // Every option shown in the UI must be a provider known by the backend.
    // (The UI may hide providers the backend returns — that is acceptable —
    //  but it must never invent providers the backend doesn't know about.)
    for (const providerId of uiProviderIds) {
      expect(
        backendProviderIds,
        `UI shows provider "${providerId}" but backend did not return it`,
      ).toContain(providerId);
    }
  });
});
