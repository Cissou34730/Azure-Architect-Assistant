/**
 * Settings API Client
 * Provides access to application settings including LLM model management.
 */

import { API_BASE } from "./config";
import { fetchWithErrorHandling } from "./serviceError";

/**
 * Pricing information for a model
 */
export interface PricingInfo {
  readonly input: number; // Input tokens price per 1K tokens
  readonly output: number; // Output tokens price per 1K tokens
  readonly currency: string; // Currency code (e.g., USD)
}

/**
 * Model information
 */
export interface ModelInfo {
  readonly id: string;
  readonly name: string;
  readonly contextWindow: number;
  readonly pricing: PricingInfo | null;
}

/**
 * Available models response
 */
export interface AvailableModelsResponse {
  readonly models: readonly ModelInfo[];
  readonly cachedAt: string; // ISO datetime string
}

/**
 * Current model response
 */
export interface CurrentModelResponse {
  readonly model: string;
}

/**
 * Set model response
 */
export interface SetModelResponse {
  readonly success: boolean;
  readonly currentModel: string;
  readonly message: string | null;
}

/**
 * Settings API client
 */
export const settingsApi = {
  /**
   * Fetch available OpenAI chat completion models.
   * Models are cached with a 7-day TTL.
   *
   * @param refresh - Force refresh from OpenAI API, bypassing cache
   * @returns List of available models with pricing
   */
  async fetchAvailableModels(
    refresh = false,
  ): Promise<AvailableModelsResponse> {
    const url = `${API_BASE}/settings/available-models${refresh ? "?refresh=true" : ""}`;

    // Backend API uses snake_case, we map to camelCase
    /* eslint-disable @typescript-eslint/naming-convention */
    const data = await fetchWithErrorHandling<{
      readonly models: readonly {
        readonly id: string;
        readonly name: string;
        readonly context_window: number;
        readonly pricing: PricingInfo | null;
      }[];
      readonly cached_at: string;
    }>(url, {}, "fetch available models");
    /* eslint-enable @typescript-eslint/naming-convention */

    // Map snake_case API response to camelCase
    return {
      models: data.models.map((m) => ({
        id: m.id,
        name: m.name,
        contextWindow: m.context_window,
        pricing: m.pricing,
      })),
      cachedAt: data.cached_at,
    };
  },

  /**
   * Get the currently active LLM model.
   *
   * @returns Current model ID
   */
  async getCurrentModel(): Promise<string> {
    const data = await fetchWithErrorHandling<CurrentModelResponse>(
      `${API_BASE}/settings/current-model`,
      {},
      "get current model",
    );
    return data.model;
  },

  /**
   * Change the active LLM model.
   * This will reinitialize the AI service with the new model.
   *
   * @param modelId - Model ID to set as active
   * @returns Operation result
   */
  async setModel(modelId: string): Promise<SetModelResponse> {
    // Backend API uses snake_case, we map to camelCase
    /* eslint-disable @typescript-eslint/naming-convention */
    const data = await fetchWithErrorHandling<{
      readonly success: boolean;
      readonly current_model: string;
      readonly message: string | null;
    }>(
      `${API_BASE}/settings/model`,
      {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          model_id: modelId,
        }),
      },
      "set model",
    );
    /* eslint-enable @typescript-eslint/naming-convention */

    // Map snake_case API response to camelCase
    return {
      success: data.success,
      currentModel: data.current_model,
      message: data.message,
    };
  },
};
