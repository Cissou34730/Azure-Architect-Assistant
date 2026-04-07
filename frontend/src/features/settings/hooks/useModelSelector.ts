/**
 * useModelSelector hook for provider-aware LLM runtime selection.
 */
/* eslint-disable max-lines -- complex provider-aware hook; callbacks and effects are cohesive and interdependent */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  settingsApi,
  type LLMOptionsResponse,
  type LLMProviderInfo,
  type ModelInfo,
} from "../api/settingsService";

interface ModelSelectorState {
  readonly providers: readonly LLMProviderInfo[];
  readonly activeProvider: string;
  readonly activeModel: string;
  readonly selectedProvider: string;
  readonly selectedModel: string;
  readonly isLoading: boolean;
  readonly isRefreshing: boolean;
  readonly isSetting: boolean;
  readonly isAuthenticating: boolean;
  readonly error: string | null;
}

interface UseModelSelectorResult extends ModelSelectorState {
  readonly models: readonly ModelInfo[];
  readonly activeProviderInfo: LLMProviderInfo | undefined;
  readonly fetchOptions: () => Promise<void>;
  readonly refreshOptions: () => Promise<void>;
  readonly selectProvider: (providerId: string) => void;
  readonly setProviderAndModel: (providerId: string, modelId: string) => Promise<void>;
  readonly connectCopilot: () => Promise<void>;
  readonly disconnectCopilot: () => Promise<void>;
}

function getProviderModels(
  providers: readonly LLMProviderInfo[],
  providerId: string,
): readonly ModelInfo[] {
  return providers.find((provider) => provider.id === providerId)?.models ?? [];
}

async function fetchOptionsData(forceRefresh: boolean): Promise<LLMOptionsResponse> {
  return settingsApi.fetchLLMOptions(forceRefresh);
}

// eslint-disable-next-line max-lines-per-function -- complex provider-aware hook with multiple interdependent useCallback/useEffect hooks
export function useModelSelector(): UseModelSelectorResult {
  const [state, setState] = useState<ModelSelectorState>({
    providers: [],
    activeProvider: "",
    activeModel: "",
    selectedProvider: "",
    selectedModel: "",
    isLoading: true,
    isRefreshing: false,
    isSetting: false,
    isAuthenticating: false,
    error: null,
  });

  // Track providers that have already been auto-refreshed to prevent infinite loops
  // when a provider consistently returns 0 models (e.g. Azure not configured).
  const autoRefreshedProviders = useRef(new Set());

  const applyFetchedOptions = useCallback(
    (
      data: LLMOptionsResponse,
      {
        preferredProvider,
        preserveDraftSelection = false,
      }: {
        preferredProvider?: string;
        preserveDraftSelection?: boolean;
      } = {},
    ) => {
      setState((prev) => {
        const targetProvider =
          preferredProvider != null &&
          data.providers.some((provider) => provider.id === preferredProvider)
            ? preferredProvider
            : data.activeProvider;
        const selectedProvider = preserveDraftSelection ? prev.selectedProvider : targetProvider;
        const effectiveSelectedProvider =
          data.providers.some((provider) => provider.id === selectedProvider)
            ? selectedProvider
            : targetProvider;
        const providerModels = getProviderModels(data.providers, effectiveSelectedProvider);
        const selectedModel =
          effectiveSelectedProvider === data.activeProvider
            ? data.activeModel
            : providerModels[0]?.id ?? "";

        return {
          ...prev,
          providers: data.providers,
          activeProvider: data.activeProvider,
          activeModel: data.activeModel,
          selectedProvider: effectiveSelectedProvider,
          selectedModel,
          isLoading: false,
          isRefreshing: false,
          isSetting: false,
          error: null,
        };
      });
    },
    [],
  );

  const fetchOptions = useCallback(async () => {
    try {
      setState((prev) => ({ ...prev, isLoading: true, error: null }));
      const data = await fetchOptionsData(false);
      applyFetchedOptions(data);
    } catch (err) {
      setState((prev) => ({
        ...prev,
        isLoading: false,
        isRefreshing: false,
        error: err instanceof Error ? err.message : "Failed to fetch LLM options",
      }));
    }
  }, [applyFetchedOptions]);

  const refreshOptions = useCallback(async () => {
    try {
      autoRefreshedProviders.current.clear();
      setState((prev) => ({ ...prev, isRefreshing: true, error: null }));
      const data = await fetchOptionsData(true);
      applyFetchedOptions(data, { preferredProvider: state.selectedProvider });
    } catch (err) {
      setState((prev) => ({
        ...prev,
        isRefreshing: false,
        error: err instanceof Error ? err.message : "Failed to refresh LLM options",
      }));
    }
  }, [applyFetchedOptions, state.selectedProvider]);

  const setProviderAndModel = useCallback(
    async (providerId: string, modelId: string) => {
      try {
        setState((prev) => ({ ...prev, isSetting: true, error: null }));
        const response = await settingsApi.setLLMSelection(providerId, modelId);
        if (
          !response.success ||
          response.currentProvider !== providerId ||
          response.currentModel !== modelId
        ) {
          throw new Error(response.message ?? "Failed to change provider/model");
        }
        const data = await fetchOptionsData(false);
        applyFetchedOptions(data);
      } catch (err) {
        setState((prev) => ({
          ...prev,
          selectedProvider: prev.activeProvider,
          selectedModel: prev.activeModel,
          isSetting: false,
          error: err instanceof Error ? err.message : "Failed to change provider/model",
        }));
        throw err;
      }
    },
    [applyFetchedOptions],
  );

  const selectProvider = useCallback((providerId: string) => {
    setState((prev) => {
      const isSameAsActive = providerId === prev.activeProvider;
      return {
        ...prev,
        selectedProvider: providerId,
        selectedModel: isSameAsActive
          ? prev.activeModel
          : getProviderModels(prev.providers, providerId)[0]?.id ?? "",
        error: null,
      };
    });
  }, []);

  const connectCopilot = useCallback(async () => {
    try {
      setState((prev) => ({ ...prev, isAuthenticating: true, error: null }));
      await settingsApi.launchCopilotLogin();
      const data = await fetchOptionsData(true);
      applyFetchedOptions(data, { preferredProvider: "copilot" });
      setState((prev) => ({ ...prev, isAuthenticating: false }));
    } catch (err) {
      setState((prev) => ({
        ...prev,
        isAuthenticating: false,
        error: err instanceof Error ? err.message : "Failed to launch Copilot login",
      }));
    }
  }, [applyFetchedOptions]);

  const disconnectCopilot = useCallback(async () => {
    try {
      setState((prev) => ({ ...prev, isAuthenticating: true, error: null }));
      await settingsApi.logoutCopilot();
      const data = await fetchOptionsData(true);
      applyFetchedOptions(data);
      setState((prev) => ({ ...prev, isAuthenticating: false }));
    } catch (err) {
      setState((prev) => ({
        ...prev,
        isAuthenticating: false,
        error: err instanceof Error ? err.message : "Failed to disconnect Copilot",
      }));
    }
  }, [applyFetchedOptions]);

  useEffect(() => {
    void fetchOptions();
  }, [fetchOptions]);

  useEffect(() => {
    if (state.selectedProvider !== "copilot") {
      return;
    }

    const copilotProvider = state.providers.find((provider) => provider.id === "copilot");
    if (copilotProvider?.auth != null || state.isLoading || state.isRefreshing) {
      return;
    }

    void (async () => {
      try {
        const auth = await settingsApi.fetchCopilotStatus();
        setState((prev) => ({
          ...prev,
          providers: prev.providers.map((provider) =>
            provider.id === "copilot" ? { ...provider, auth } : provider,
          ),
        }));
      } catch {
        // Keep the provider usable even if status lookup fails.
      }
    })();
  }, [state.isLoading, state.isRefreshing, state.providers, state.selectedProvider]);

  useEffect(() => {
    if (state.isLoading || state.isRefreshing || state.isSetting) {
      return;
    }
    if (state.selectedProvider === "" || state.selectedProvider === state.activeProvider) {
      return;
    }
    if (getProviderModels(state.providers, state.selectedProvider).length > 0) {
      return;
    }
    if (autoRefreshedProviders.current.has(state.selectedProvider)) {
      return;
    }

    autoRefreshedProviders.current.add(state.selectedProvider);

    void (async () => {
      try {
        setState((prev) => ({ ...prev, isRefreshing: true, error: null }));
        const data = await fetchOptionsData(true);
        applyFetchedOptions(data, { preferredProvider: state.selectedProvider });
      } catch (err) {
        setState((prev) => ({
          ...prev,
          isRefreshing: false,
          error: err instanceof Error ? err.message : "Failed to refresh provider models",
        }));
      }
    })();
  }, [
    applyFetchedOptions,
    state.activeProvider,
    state.isLoading,
    state.isRefreshing,
    state.isSetting,
    state.providers,
    state.selectedProvider,
  ]);

  const models = useMemo(
    () => getProviderModels(state.providers, state.selectedProvider),
    [state.providers, state.selectedProvider],
  );

  const activeProviderInfo = useMemo(
    () => state.providers.find((provider) => provider.id === state.selectedProvider),
    [state.providers, state.selectedProvider],
  );

  return {
    ...state,
    models,
    activeProviderInfo,
    fetchOptions,
    refreshOptions,
    selectProvider,
    setProviderAndModel,
    connectCopilot,
    disconnectCopilot,
  };
}
