import { expect, test } from "@playwright/test";
import type { Locator, Page } from "@playwright/test";

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

function hasStringProperty(candidate: object, propertyName: string): boolean {
  return typeof Reflect.get(candidate, propertyName) === "string";
}

function hasNullableStringProperty(candidate: object, propertyName: string): boolean {
  const propertyValue = Reflect.get(candidate, propertyName);
  return propertyValue === null || typeof propertyValue === "string";
}

function hasNullableObjectProperty(candidate: object, propertyName: string): boolean {
  const propertyValue = Reflect.get(candidate, propertyName);
  return propertyValue === null || typeof propertyValue === "object";
}

function hasBooleanProperty(candidate: object, propertyName: string): boolean {
  return typeof Reflect.get(candidate, propertyName) === "boolean";
}

function isBackendModel(value: object | null): value is BackendModel {
  if (value === null) {
    return false;
  }

  return hasStringProperty(value, "id") &&
    hasStringProperty(value, "name") &&
    typeof Reflect.get(value, "context_window") === "number" &&
    hasNullableObjectProperty(value, "pricing");
}

function isBackendProvider(value: object | null): value is BackendProvider {
  if (value === null) {
    return false;
  }

  const providerModels = Reflect.get(value, "models");
  return hasStringProperty(value, "id") &&
    hasStringProperty(value, "name") &&
    hasStringProperty(value, "status") &&
    hasNullableStringProperty(value, "status_message") &&
    hasBooleanProperty(value, "selected") &&
    Array.isArray(providerModels) &&
    providerModels.every(isBackendModel);
}

function isBackendLLMOptionsResponse(value: object | null): value is BackendLLMOptionsResponse {
  if (value === null) {
    return false;
  }

  const responseProviders = Reflect.get(value, "providers");
  return hasStringProperty(value, "active_provider") &&
    hasStringProperty(value, "active_model") &&
    Array.isArray(responseProviders) &&
    responseProviders.every(isBackendProvider);
}

async function readEnabledOptionValues(selectLocator: Locator): Promise<string[]> {
  return selectLocator.locator("option").evaluateAll((optionElements) =>
    optionElements
      .filter(
        (optionElement): optionElement is HTMLOptionElement =>
          optionElement instanceof HTMLOptionElement && !optionElement.disabled,
      )
      .map((optionElement) => optionElement.value)
      .filter((optionValue) => optionValue !== "" && optionValue !== "__refresh__"),
  );
}

async function fetchBackendOptions(page: Page, refresh = false): Promise<BackendLLMOptionsResponse> {
  const apiResponse = await page.request.get(
    `${BACKEND_BASE_URL}/api/settings/llm-options${refresh ? "?refresh=true" : ""}`,
  );
  expect(
    apiResponse.ok(),
    `Backend /api/settings/llm-options${refresh ? "?refresh=true" : ""} returned HTTP ${apiResponse.status()}`,
  ).toBe(true);

  const responsePayload = await apiResponse.json();
  expect(isBackendLLMOptionsResponse(responsePayload)).toBe(true);
  if (!isBackendLLMOptionsResponse(responsePayload)) {
    throw new Error("Unexpected /api/settings/llm-options response payload.");
  }
  return responsePayload;
}

async function expectInitialModelsLoaded(modelSelect: Locator): Promise<void> {
  await expect(
    modelSelect,
    "Model picker dropdown is not visible on the page",
  ).toBeVisible({ timeout: 20_000 });

  await expect(async () => {
    const enabledOptions = await readEnabledOptionValues(modelSelect);
    expect(enabledOptions.length).toBeGreaterThan(0);
  }).toPass({ timeout: 30_000 });
}

test("model dropdown matches the live backend model list for the active provider", async ({ page }) => {
  test.setTimeout(60_000);

  await page.goto("/");

  const modelSelect = page.locator('select[aria-label="LLM Model"]');
  await expectInitialModelsLoaded(modelSelect);

  // The initial load may return a cached subset. The refresh sentinel asks the
  // active provider, including Azure AI Foundry, for its full deployed model list.
  await modelSelect.selectOption("__refresh__");
  await expect(
    modelSelect.locator('option[value="__refresh__"]'),
    "Refresh did not complete within timeout",
  ).toHaveText("Refresh models", { timeout: 30_000 });

  const backendOptions = await fetchBackendOptions(page, true);
  const activeProvider = backendOptions.providers.find(
    (provider) => provider.id === backendOptions.active_provider,
  );
  expect(
    activeProvider,
    `Active provider "${backendOptions.active_provider}" not found in providers list`,
  ).toBeDefined();
  if (activeProvider === undefined) {
    return;
  }

  const backendModelIds = activeProvider.models.map((backendModel) => backendModel.id);
  console.log(
    `Backend (refreshed): active provider = "${backendOptions.active_provider}", ` +
      `${backendModelIds.length} model(s): ${backendModelIds.join(", ")}`,
  );
  if (backendModelIds.length === 0) {
    console.warn(
      `Provider "${backendOptions.active_provider}" has 0 models after refresh — ` +
        "skipping UI comparison (environment not fully configured).",
    );
    return;
  }

  await expect(async () => {
    const currentUiModelIds = await readEnabledOptionValues(modelSelect);
    expect(currentUiModelIds.length).toBe(backendModelIds.length);
  }).toPass({ timeout: 30_000 });

  const uiModelIds = await readEnabledOptionValues(modelSelect);
  console.log(`UI dropdown (refreshed): ${uiModelIds.length} model(s): ${uiModelIds.join(", ")}`);

  for (const backendModelId of backendModelIds) {
    expect(uiModelIds, `Backend model "${backendModelId}" is missing from the UI model picker`).toContain(
      backendModelId,
    );
  }
  for (const uiModelId of uiModelIds) {
    expect(backendModelIds, `UI model picker shows "${uiModelId}" but the backend did not return it`).toContain(
      uiModelId,
    );
  }
  expect(
    uiModelIds.length,
    `UI has ${uiModelIds.length} models but backend returned ${backendModelIds.length}`,
  ).toBe(backendModelIds.length);
});

test("provider picker only shows providers that the backend knows about", async ({ page }) => {
  test.setTimeout(60_000);

  const backendOptions = await fetchBackendOptions(page);
  const backendProviderIds = backendOptions.providers.map((provider) => provider.id);
  console.log(
    `Backend providers: ${backendProviderIds.join(", ")} (active: ${backendOptions.active_provider})`,
  );

  await page.goto("/");

  const providerSelect = page.locator('select[aria-label="LLM Provider"]');
  await expect(providerSelect).toBeVisible({ timeout: 20_000 });
  await expect(
    providerSelect.locator(`option[value="${backendOptions.active_provider}"]`),
    `Active provider "${backendOptions.active_provider}" must appear in the provider picker`,
  ).toBeAttached({ timeout: 15_000 });

  const uiProviderIds = await readEnabledOptionValues(providerSelect);
  console.log(`UI providers: ${uiProviderIds.join(", ")}`);

  for (const uiProviderId of uiProviderIds) {
    expect(backendProviderIds, `UI shows provider "${uiProviderId}" but backend did not return it`).toContain(
      uiProviderId,
    );
  }
});
