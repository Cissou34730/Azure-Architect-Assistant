import { useCallback, type ChangeEvent } from "react";
import { useModelSelector } from "../hooks/useModelSelector";
import { useTheme, type ThemePreference } from "../../../shared/hooks/useTheme";
import type {
  LLMProviderInfo,
  ModelInfo,
  PricingInfo,
} from "../api/settingsService";

const REFRESH_OPTION_VALUE = "__refresh__";

const THEME_OPTIONS: readonly { value: ThemePreference; label: string }[] = [
  { value: "system", label: "System" },
  { value: "light", label: "Light" },
  { value: "dark", label: "Dark" },
];

function isThemePreference(value: string): value is ThemePreference {
  return THEME_OPTIONS.some((option) => option.value === value);
}

function formatPricing(pricing: PricingInfo | null): string {
  if (pricing == null) {
    return "";
  }
  const inputPrice = pricing.input.toFixed(4).replace(/\.?0+$/, "");
  const outputPrice = pricing.output.toFixed(4).replace(/\.?0+$/, "");
  return `$${inputPrice}/$${outputPrice}`;
}

function getPricingLabel(model: ModelInfo): string {
  const pricing = formatPricing(model.pricing);
  return pricing.length > 0 ? `${model.name} - ${pricing}` : model.name;
}

function handleThemePreferenceChange(
  event: ChangeEvent<HTMLSelectElement>,
  setPreference: (themePreference: ThemePreference) => void,
): void {
  const selectedTheme = event.target.value;
  if (isThemePreference(selectedTheme)) {
    setPreference(selectedTheme);
  }
}

function handleProviderSelectionChange(
  event: ChangeEvent<HTMLSelectElement>,
  selectProvider: (providerId: string) => void,
): void {
  selectProvider(event.target.value);
}

async function handleModelSelectionChange({
  event,
  selectedProvider,
  refreshOptions,
  setProviderAndModel,
}: {
  readonly event: ChangeEvent<HTMLSelectElement>;
  readonly selectedProvider: string;
  readonly refreshOptions: () => Promise<void>;
  readonly setProviderAndModel: (providerId: string, modelId: string) => Promise<void>;
}): Promise<void> {
  const value = event.target.value;
  if (value === REFRESH_OPTION_VALUE) {
    await refreshOptions();
    return;
  }
  await setProviderAndModel(selectedProvider, value);
}

async function handleCopilotAuthAction(
  activeProviderInfo: LLMProviderInfo | undefined,
  connectCopilot: () => Promise<void>,
  disconnectCopilot: () => Promise<void>,
): Promise<void> {
  const auth = activeProviderInfo?.auth;
  if (auth?.authenticated) {
    await disconnectCopilot();
    return;
  }
  await connectCopilot();
}

export function NavigationSettingsControls() {
  const { preference, setPreference } = useTheme();
  const {
    providers,
    models,
    selectedProvider,
    selectedModel,
    activeProviderInfo,
    isLoading,
    isRefreshing,
    isSetting,
    isAuthenticating,
    error,
    refreshOptions,
    selectProvider,
    setProviderAndModel,
    connectCopilot,
    disconnectCopilot,
  } = useModelSelector();

  const handleThemeChange = useCallback(
    (event: ChangeEvent<HTMLSelectElement>): void => {
      handleThemePreferenceChange(event, setPreference);
    },
    [setPreference],
  );

  const handleProviderChange = useCallback(
    (event: ChangeEvent<HTMLSelectElement>): void => {
      handleProviderSelectionChange(event, selectProvider);
    },
    [selectProvider],
  );

  const handleModelChange = useCallback(
    async (event: ChangeEvent<HTMLSelectElement>): Promise<void> => {
      await handleModelSelectionChange({
        event,
        selectedProvider,
        refreshOptions,
        setProviderAndModel,
      });
    },
    [refreshOptions, selectedProvider, setProviderAndModel],
  );

  const handleCopilotAuth = useCallback(async (): Promise<void> => {
    await handleCopilotAuthAction(
      activeProviderInfo,
      connectCopilot,
      disconnectCopilot,
    );
  }, [activeProviderInfo, connectCopilot, disconnectCopilot]);

  return (
    <>
      <ProviderSelector
        providers={providers}
        selectedProvider={selectedProvider}
        disabled={isLoading || isRefreshing}
        onProviderChange={handleProviderChange}
      />
      <ModelSelector
        models={models}
        selectedModel={selectedModel}
        disabled={isLoading || isRefreshing || isSetting}
        isRefreshing={isRefreshing}
        error={error}
        providerStatusMessage={activeProviderInfo?.statusMessage ?? null}
        onModelChange={handleModelChange}
      />
      {selectedProvider === "copilot" && (
        <CopilotAuthChip
          provider={activeProviderInfo}
          disabled={isLoading || isRefreshing || isSetting || isAuthenticating}
          onClick={handleCopilotAuth}
        />
      )}
      <ThemeSelector preference={preference} onThemeChange={handleThemeChange} />
    </>
  );
}

function ProviderSelector({
  providers,
  selectedProvider,
  disabled,
  onProviderChange,
}: {
  readonly providers: readonly LLMProviderInfo[];
  readonly selectedProvider: string;
  readonly disabled: boolean;
  readonly onProviderChange: (event: ChangeEvent<HTMLSelectElement>) => void;
}) {
  return (
    <select
      value={selectedProvider}
      onChange={onProviderChange}
      disabled={disabled}
      className="rounded-md border border-border-stronger bg-card px-2 py-1 text-xs text-secondary focus:outline-none focus:ring-2 focus:ring-brand disabled:opacity-50"
      aria-label="LLM Provider"
    >
      {providers.map((provider) => (
        <option key={provider.id} value={provider.id}>
          {provider.models.length === 0 && provider.status === "error"
            ? `${provider.name} (not configured)`
            : provider.name}
        </option>
      ))}
    </select>
  );
}

function ModelSelector({
  models,
  selectedModel,
  disabled,
  isRefreshing,
  error,
  providerStatusMessage,
  onModelChange,
}: {
  readonly models: readonly ModelInfo[];
  readonly selectedModel: string;
  readonly disabled: boolean;
  readonly isRefreshing: boolean;
  readonly error: string | null;
  readonly providerStatusMessage: string | null;
  readonly onModelChange: (event: ChangeEvent<HTMLSelectElement>) => Promise<void>;
}) {
  return (
    <select
      value={selectedModel}
      onChange={(event) => void onModelChange(event)}
      disabled={disabled}
      className="rounded-md border border-border-stronger bg-card px-2 py-1 text-xs text-secondary focus:outline-none focus:ring-2 focus:ring-brand disabled:opacity-50"
      aria-label="LLM Model"
      title={error ?? undefined}
    >
      {models.length === 0 && (
        <option value="" disabled>
          {providerStatusMessage ?? "No models available"}
        </option>
      )}
      {selectedModel === "" && (
        <option value="" disabled>
          Select model
        </option>
      )}
      {models.map((model) => (
        <option key={model.id} value={model.id}>
          {getPricingLabel(model)}
        </option>
      ))}
      <option disabled>──────────</option>
      <option value={REFRESH_OPTION_VALUE}>
        {isRefreshing ? "Refreshing models..." : "Refresh models"}
      </option>
    </select>
  );
}

function CopilotAuthChip({
  provider,
  disabled,
  onClick,
}: {
  readonly provider: LLMProviderInfo | undefined;
  readonly disabled: boolean;
  readonly onClick: () => Promise<void>;
}) {
  const auth = provider?.auth;
  const label = auth?.authenticated ? `Copilot: ${auth.login ?? "connected"}` : "Connect Copilot";
  const title = auth?.statusMessage ?? undefined;

  return (
    <button
      type="button"
      onClick={() => void onClick()}
      disabled={disabled}
      title={title}
      className="rounded-md border border-border-stronger bg-card px-2 py-1 text-xs text-secondary focus:outline-none focus:ring-2 focus:ring-brand disabled:opacity-50"
    >
      {label}
    </button>
  );
}

function ThemeSelector({
  preference,
  onThemeChange,
}: {
  readonly preference: ThemePreference;
  readonly onThemeChange: (event: ChangeEvent<HTMLSelectElement>) => void;
}) {
  return (
    <select
      value={preference}
      onChange={onThemeChange}
      className="rounded-md border border-border-stronger bg-card px-2 py-1 text-xs text-secondary focus:outline-none focus:ring-2 focus:ring-brand"
      aria-label="Theme"
    >
      {THEME_OPTIONS.map((option) => (
        <option key={option.value} value={option.value}>
          {option.label}
        </option>
      ))}
    </select>
  );
}