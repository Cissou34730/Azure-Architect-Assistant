import { renderHook, act, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";

import type { LLMOptionsResponse } from "../api/settingsService";
import { settingsApi } from "../api/settingsService";
import { useModelSelector } from "./useModelSelector";

vi.mock("../api/settingsService", () => ({
  settingsApi: {
    fetchLLMOptions: vi.fn(),
    setLLMSelection: vi.fn(),
    fetchCopilotStatus: vi.fn(),
    launchCopilotLogin: vi.fn(),
    logoutCopilot: vi.fn(),
  },
}));

const fetchLLMOptions = vi.mocked(settingsApi.fetchLLMOptions);

function makeResponse(overrides?: Partial<LLMOptionsResponse>): LLMOptionsResponse {
  return {
    activeProvider: "openai",
    activeModel: "gpt-4o",
    providers: [
      {
        id: "openai",
        name: "OpenAI",
        status: "ready",
        statusMessage: null,
        selected: true,
        models: [{ id: "gpt-4o", name: "GPT-4o", contextWindow: 128000, pricing: null }],
        auth: null,
      },
      {
        id: "foundry",
        name: "Azure AI Foundry",
        status: "error",
        statusMessage: "Foundry endpoint, API key, resource id, and runtime model required for Foundry provider",
        selected: false,
        models: [],
        auth: null,
      },
      {
        id: "copilot",
        name: "GitHub Copilot",
        status: "ready",
        statusMessage: null,
        selected: false,
        models: [{ id: "gpt-4o", name: "GPT-4o", contextWindow: 128000, pricing: null }],
        auth: null,
      },
    ],
    ...overrides,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("useModelSelector", () => {
  it("does not loop when selecting a provider that returns 0 models", async () => {
    // Foundry always returns 0 models (not configured).
    fetchLLMOptions.mockResolvedValue(makeResponse());

    const { result } = renderHook(() => useModelSelector());

    // Wait for initial fetch to settle.
    await waitFor(() => { expect(result.current.isLoading).toBe(false); });

    // The initial mount should have called fetchLLMOptions once.
    const callsAfterMount = fetchLLMOptions.mock.calls.length;
    expect(callsAfterMount).toBe(1);

    // User selects Foundry (which has 0 models and status "error").
    act(() => {
      result.current.selectProvider("foundry");
    });

    // The third useEffect may fire ONE refresh attempt (refresh=true).
    // Allow a generous window for any async effects to settle.
    await waitFor(() => { expect(result.current.isRefreshing).toBe(false); }, { timeout: 2000 });

    // The key assertion: at most 1 extra refresh call, NOT an infinite loop.
    // Mount call (refresh=false) + at most 1 auto-refresh (refresh=true) = max 2.
    expect(fetchLLMOptions.mock.calls.length).toBeLessThanOrEqual(callsAfterMount + 1);
  });

  it("does not loop for a provider with status ready but 0 models", async () => {
    // Foundry returns status "ready" but still with 0 models.
    const response = makeResponse();
    const patchedProviders = response.providers.map((p) =>
      p.id === "foundry" ? { ...p, status: "ready", statusMessage: null } : p,
    );
    fetchLLMOptions.mockResolvedValue({ ...response, providers: patchedProviders });

    const { result } = renderHook(() => useModelSelector());
    await waitFor(() => { expect(result.current.isLoading).toBe(false); });

    const callsAfterMount = fetchLLMOptions.mock.calls.length;

    act(() => {
      result.current.selectProvider("foundry");
    });

    await waitFor(() => { expect(result.current.isRefreshing).toBe(false); }, { timeout: 2000 });

    // Max 1 extra refresh, never an infinite loop.
    expect(fetchLLMOptions.mock.calls.length).toBeLessThanOrEqual(callsAfterMount + 1);
  });

  it("exposes provider statusMessage when selecting an errored provider", async () => {
    fetchLLMOptions.mockResolvedValue(makeResponse());

    const { result } = renderHook(() => useModelSelector());
    await waitFor(() => { expect(result.current.isLoading).toBe(false); });

    act(() => {
      result.current.selectProvider("foundry");
    });

    await waitFor(() => { expect(result.current.isRefreshing).toBe(false); }, { timeout: 2000 });

    // activeProviderInfo should reflect the errored Foundry provider with its message.
    expect(result.current.activeProviderInfo?.id).toBe("foundry");
    expect(result.current.activeProviderInfo?.status).toBe("error");
    expect(result.current.activeProviderInfo?.statusMessage).toBe(
      "Foundry endpoint, API key, resource id, and runtime model required for Foundry provider",
    );
    expect(result.current.models).toHaveLength(0);
  });
});
