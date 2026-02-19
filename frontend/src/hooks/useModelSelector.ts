/**
 * useModelSelector Hook
 * Manages LLM model selection state and operations.
 */

import {
  useCallback,
  useEffect,
  useState,
  type Dispatch,
  type SetStateAction,
} from "react";
import { settingsApi } from "../services/settingsService";
import type { ModelInfo } from "../services/settingsService";

interface ModelSelectorState {
  readonly models: readonly ModelInfo[];
  readonly selectedModel: string;
  readonly isLoading: boolean;
  readonly isRefreshing: boolean;
  readonly isSetting: boolean;
  readonly error: string | null;
}

interface UseModelSelectorResult extends ModelSelectorState {
  readonly fetchModels: () => Promise<void>;
  readonly refreshModels: () => Promise<void>;
  readonly setModel: (modelId: string) => Promise<void>;
}

/**
 * Fetch models and current selection from API.
 */
async function fetchModelsData(forceRefresh: boolean): Promise<{
  models: readonly ModelInfo[];
  selectedModel: string;
}> {
  const [modelsResponse, currentModel] = await Promise.all([
    settingsApi.fetchAvailableModels(forceRefresh),
    settingsApi.getCurrentModel(),
  ]);

  return {
    models: modelsResponse.models,
    selectedModel: currentModel,
  };
}

/**
 * Hook for managing LLM model selection.
 */
export function useModelSelector(): UseModelSelectorResult {
  const [state, setState] = useState<ModelSelectorState>({
    models: [],
    selectedModel: "",
    isLoading: true,
    isRefreshing: false,
    isSetting: false,
    error: null,
  });

  const fetchModels = useFetchModels(setState);
  const refreshModels = useRefreshModels(setState);
  const setModel = useSetModel(setState);

  // Fetch models on mount
  useEffect(() => {
    void fetchModels();
  }, [fetchModels]);

  return { ...state, fetchModels, refreshModels, setModel };
}

/**
 * Hook for fetching models operation.
 */
function useFetchModels(
  setState: Dispatch<SetStateAction<ModelSelectorState>>,
): () => Promise<void> {
  return useCallback(async () => {
    try {
      setState((prev) => ({ ...prev, isLoading: true, error: null }));
      const data = await fetchModelsData(false);
      setState((prev) => ({
        ...prev,
        ...data,
        isLoading: false,
        isRefreshing: false,
        error: null,
      }));
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : "Failed to fetch models";
      setState((prev) => ({
        ...prev,
        isLoading: false,
        isRefreshing: false,
        error: errorMessage,
      }));
    }
  }, [setState]);
}

/**
 * Hook for refreshing models operation.
 */
function useRefreshModels(
  setState: Dispatch<SetStateAction<ModelSelectorState>>,
): () => Promise<void> {
  return useCallback(async () => {
    try {
      setState((prev) => ({ ...prev, isRefreshing: true, error: null }));
      const data = await fetchModelsData(true);
      setState((prev) => ({
        ...prev,
        ...data,
        isLoading: false,
        isRefreshing: false,
        error: null,
      }));
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : "Failed to refresh models";
      setState((prev) => ({
        ...prev,
        isRefreshing: false,
        error: errorMessage,
      }));
    }
  }, [setState]);
}

/**
 * Hook for setting model operation.
 */
function useSetModel(
  setState: Dispatch<SetStateAction<ModelSelectorState>>,
): (modelId: string) => Promise<void> {
  return useCallback(
    async (modelId: string) => {
      let previousModel = "";

      try {
        setState((prev) => {
          previousModel = prev.selectedModel;
          return {
            ...prev,
            selectedModel: modelId,
            isSetting: true,
            error: null,
          };
        });

        const response = await settingsApi.setModel(modelId);

        if (!response.success || response.currentModel !== modelId) {
          throw new Error(response.message ?? "Failed to change model");
        }

        const syncedData = await fetchModelsData(false);

        setState((prev) => ({
          ...prev,
          ...syncedData,
          isLoading: false,
          isRefreshing: false,
          isSetting: false,
          error: null,
        }));
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : "Failed to set model";
        setState((prev) => ({
          ...prev,
          selectedModel: previousModel,
          isSetting: false,
          error: errorMessage,
        }));
        throw err;
      }
    },
    [setState],
  );
}
