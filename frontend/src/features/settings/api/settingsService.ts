/**
 * Settings API client for provider-aware LLM runtime management.
 */

import { API_BASE } from "../../../shared/config/api";
import { fetchWithErrorHandling } from "../../../shared/http/fetchWithErrorHandling";

export interface PricingInfo {
  readonly input: number;
  readonly output: number;
  readonly currency: string;
}

export interface ModelInfo {
  readonly id: string;
  readonly name: string;
  readonly contextWindow: number;
  readonly pricing: PricingInfo | null;
}

export interface ProviderAuthInfo {
  readonly available: boolean;
  readonly authenticated: boolean;
  readonly state: string;
  readonly login: string | null;
  readonly authType: string | null;
  readonly host: string | null;
  readonly statusMessage: string | null;
  readonly cliPath: string | null;
  // eslint-disable-next-line @typescript-eslint/no-restricted-types -- quota is arbitrary JSON from external API
  readonly quota: Record<string, unknown> | null;
}

export interface LLMProviderInfo {
  readonly id: string;
  readonly name: string;
  readonly status: string;
  readonly statusMessage: string | null;
  readonly selected: boolean;
  readonly models: readonly ModelInfo[];
  readonly auth: ProviderAuthInfo | null;
}

export interface LLMOptionsResponse {
  readonly activeProvider: string;
  readonly activeModel: string;
  readonly providers: readonly LLMProviderInfo[];
}

export interface SetModelResponse {
  readonly success: boolean;
  readonly currentModel: string;
  readonly currentProvider: string | null;
  readonly message: string | null;
}

export interface CopilotActionResponse {
  readonly success: boolean;
  readonly launched: boolean | null;
  readonly manualLogoutRequired: boolean | null;
  readonly message: string;
}

export type CopilotStatusResponse = ProviderAuthInfo;

export interface ArchitectProfile {
  readonly defaultRegionPrimary: string;
  readonly defaultRegionSecondary: string | null;
  readonly defaultIacFlavor: "bicep" | "terraform";
  readonly complianceBaseline: readonly string[];
  readonly monthlyCostCeiling: number | null;
  readonly preferredVmSeries: readonly string[];
  readonly teamDevopsMaturity: "none" | "basic" | "advanced";
  readonly notes: string;
}

export interface ArchitectProfileResponse {
  readonly profile: ArchitectProfile;
  readonly updatedAt: string | null;
}

function mapModel(model: {
  readonly id: string;
  readonly name: string;
  readonly contextWindow: number;
  readonly pricing: PricingInfo | null;
}): ModelInfo {
  return {
    id: model.id,
    name: model.name,
    contextWindow: model.contextWindow,
    pricing: model.pricing,
  };
}

interface RawProvider {
  readonly id: string;
  readonly name: string;
  readonly status: string;
  readonly statusMessage: string | null;
  readonly selected: boolean;
  readonly models: readonly {
    readonly id: string;
    readonly name: string;
    readonly contextWindow: number;
    readonly pricing: PricingInfo | null;
  }[];
  readonly auth?: ProviderAuthInfo | null;
}

function mapProvider(provider: RawProvider): LLMProviderInfo {
  return {
    id: provider.id,
    name: provider.name,
    status: provider.status,
    statusMessage: provider.statusMessage,
    selected: provider.selected,
    models: provider.models.map(mapModel),
    auth: provider.auth ?? null,
  };
}

export const settingsApi = {
  async fetchLLMOptions(refresh = false): Promise<LLMOptionsResponse> {
    const data = await fetchWithErrorHandling<{
      readonly activeProvider: string;
      readonly activeModel: string;
      readonly providers: readonly RawProvider[];
    }>(
      `${API_BASE}/settings/llm-options${refresh ? "?refresh=true" : ""}`,
      {},
      "fetch llm options",
    );

    return {
      activeProvider: data.activeProvider,
      activeModel: data.activeModel,
      providers: data.providers.map(mapProvider),
    };
  },

  async setLLMSelection(
    providerId: string,
    modelId: string,
  ): Promise<SetModelResponse> {
    const data = await fetchWithErrorHandling<{
      readonly success: boolean;
      readonly currentModel: string;
      readonly currentProvider: string | null;
      readonly message: string | null;
    }>(
      `${API_BASE}/settings/llm-selection`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          provider_id: providerId,
          model_id: modelId,
        }),
      },
      "set llm selection",
    );

    return {
      success: data.success,
      currentModel: data.currentModel,
      currentProvider: data.currentProvider,
      message: data.message,
    };
  },

  async launchCopilotLogin(): Promise<CopilotActionResponse> {
    const data = await fetchWithErrorHandling<CopilotActionResponse>(
      `${API_BASE}/settings/copilot/login`,
      {
        method: "POST",
      },
      "launch Copilot login",
    );
    return data;
  },

  async logoutCopilot(): Promise<CopilotActionResponse> {
    const data = await fetchWithErrorHandling<CopilotActionResponse>(
      `${API_BASE}/settings/copilot/logout`,
      {
        method: "POST",
      },
      "logout Copilot",
    );
    return data;
  },

  async fetchCopilotStatus(): Promise<CopilotStatusResponse> {
    return fetchWithErrorHandling<CopilotStatusResponse>(
      `${API_BASE}/settings/copilot/status`,
      {},
      "fetch Copilot status",
    );
  },

  async fetchArchitectProfile(): Promise<ArchitectProfileResponse> {
    return fetchWithErrorHandling<ArchitectProfileResponse>(
      `${API_BASE}/settings/architect-profile`,
      {},
      "fetch architect profile",
    );
  },

  async updateArchitectProfile(profile: ArchitectProfile): Promise<ArchitectProfileResponse> {
    return fetchWithErrorHandling<ArchitectProfileResponse>(
      `${API_BASE}/settings/architect-profile`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(profile),
      },
      "update architect profile",
    );
  },
};
