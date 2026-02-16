/**
 * useModelSelector Hook
 * Manages LLM model selection state and operations.
 */

import { useCallback, useEffect, useState } from "react";
import { settingsApi } from "../services/settingsService";
import type { ModelInfo } from "../services/settingsService";

interface ModelSelectorState {
  readonly models: readonly ModelInfo[];
  readonly selectedModel: string;
  readonly isLoading: boolean;
  readonly isRefreshing: boolean;
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
    error: null,
  });

  const fetchModels = useFetchModels(setState);
  const refreshModels = useRefreshModels(setState);
  const setModel = useSetModel(state.selectedModel, setState);

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
  setState: React.Dispatch<React.SetStateAction<ModelSelectorState>>,
): () => Promise<void> {
  return useCallback(async () => {
    try {
      setState((prev) => ({ ...prev, isLoading: true, error: null }));
      const data = await fetchModelsData(false);
      setState({ ...data, isLoading: false, isRefreshing: false, error: null });
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
  setState: React.Dispatch<React.SetStateAction<ModelSelectorState>>,
): () => Promise<void> {
  return useCallback(async () => {
    try {
      setState((prev) => ({ ...prev, isRefreshing: true, error: null }));
      const data = await fetchModelsData(true);
      setState({ ...data, isLoading: false, isRefreshing: false, error: null });
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
  currentModel: string,
  setState: React.Dispatch<React.SetStateAction<ModelSelectorState>>,
): (modelId: string) => Promise<void> {
  return useCallback(
    async (modelId: string) => {
      const previousModel = currentModel;
      
      try {
        // Optimistic update
        setState((prev) => ({ ...prev, selectedModel: modelId, error: null }));
        
        // Send change request to backend
        const response = await settingsApi.setModel(modelId);

        if (!response.success || response.currentModel !== modelId) {
          throw new Error(response.message ?? "Failed to change model");
        }
        
        // Verify the actual current model from backend
        const actualCurrentModel = await settingsApi.getCurrentModel();
        
        // Update state with verified model
        setState((prev) => ({ 
          ...prev, 
          selectedModel: actualCurrentModel, 
          error: null 
        }));
        
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : "Failed to set model";
        // Rollback to previous model on error
        setState((prev) => ({
          ...prev,
          selectedModel: previousModel,
          error: errorMessage,
        }));
        throw err;
      }
    },
    [currentModel, setState],
  );
}
