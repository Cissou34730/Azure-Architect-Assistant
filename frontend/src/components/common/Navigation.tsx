import { useCallback, type ChangeEvent } from "react";
import { NavLink } from "react-router-dom";
import { useTheme, type ThemePreference } from "../../hooks/useTheme";
import { useModelSelector } from "../../hooks/useModelSelector";
import type { ModelInfo, PricingInfo } from "../../services/settingsService";

const REFRESH_OPTION_VALUE = "__refresh__";

interface NavItem {
  readonly to: string;
  readonly label: string;
  readonly ariaLabel: string;
}

const NAV_ITEMS: readonly NavItem[] = [
  {
    to: "/project",
    label: "Projects",
    ariaLabel: "View architecture projects",
  },
  {
    to: "/kb",
    label: "Knowledge Base",
    ariaLabel: "Query knowledge bases",
  },
  {
    to: "/kb-management",
    label: "KB Management",
    ariaLabel: "Manage knowledge bases",
  },
];

const THEME_OPTIONS: readonly { value: ThemePreference; label: string }[] = [
  { value: "system", label: "System" },
  { value: "light", label: "Light" },
  { value: "dark", label: "Dark" },
];

function isThemePreference(value: string): value is ThemePreference {
  return THEME_OPTIONS.some((option) => option.value === value);
}

function getModelSelectValue(isLoading: boolean, selectedModel: string): string {
  return isLoading ? "" : selectedModel;
}

function isSelectedModelPresent(
  models: readonly ModelInfo[],
  selectedModel: string,
): boolean {
  return models.some((model) => model.id === selectedModel);
}

/**
 * Format pricing information for display in dropdown.
 *
 * @param pricing - Pricing info or null
 * @returns Formatted pricing string (e.g., "$0.01/$0.03")
 */
function formatPricing(pricing: PricingInfo | null): string {
  if (pricing == null) {
    return "";
  }

  // Format to reasonable precision, removing trailing zeros
  const inputPrice = pricing.input.toFixed(4).replace(/\.?0+$/, "");
  const outputPrice = pricing.output.toFixed(4).replace(/\.?0+$/, "");

  return `$${inputPrice}/$${outputPrice}`;
}

export function Navigation() {
  const { preference, setPreference } = useTheme();
  const {
    models,
    selectedModel,
    isLoading,
    isRefreshing,
    isSetting,
    error,
    refreshModels,
    setModel: setSelectedModel,
  } = useModelSelector();

  const modelExistsInList = isSelectedModelPresent(models, selectedModel);
  const modelSelectValue = getModelSelectValue(isLoading, selectedModel);

  const handleThemeChange = useCallback(
    (event: ChangeEvent<HTMLSelectElement>): void => {
      const selectedTheme = event.target.value;
      if (isThemePreference(selectedTheme)) {
        setPreference(selectedTheme);
      }
    },
    [setPreference],
  );

  const handleModelChange = useCallback(
    async (event: ChangeEvent<HTMLSelectElement>): Promise<void> => {
      const value = event.target.value;

      if (value === REFRESH_OPTION_VALUE) {
        try {
          await refreshModels();
        } catch {
          // Error state is handled by the hook
        }
        return;
      }

      try {
        await setSelectedModel(value);
      } catch {
        // Error state is handled by the hook
      }
    },
    [refreshModels, setSelectedModel],
  );

  return (
    <nav
      className="sticky top-0 bg-card shadow-sm border-b border-border z-40"
      role="navigation"
      aria-label="Main navigation"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-14">
          <NavigationLinks />
          <div className="flex items-center gap-3">
            <ModelSelector
              models={models}
              selectedModel={selectedModel}
              modelSelectValue={modelSelectValue}
              modelExistsInList={modelExistsInList}
              isLoading={isLoading}
              isRefreshing={isRefreshing}
              isSetting={isSetting}
              error={error}
              onModelChange={handleModelChange}
            />
            <ThemeSelector
              preference={preference}
              onThemeChange={handleThemeChange}
            />
            <div className="text-sm text-secondary">Azure Architect Assistant</div>
          </div>
        </div>
      </div>
    </nav>
  );
}

function NavigationLinks() {
  return (
    <div className="flex space-x-8">
      {NAV_ITEMS.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          aria-label={item.ariaLabel}
          className={({ isActive }: { isActive: boolean }) =>
            `px-3 py-2 text-sm font-medium transition-colors ${
              isActive
                ? "text-brand border-b-2 border-brand"
                : "text-secondary hover:text-foreground"
            }`
          }
        >
          {item.label}
        </NavLink>
      ))}
    </div>
  );
}

function getPricingLabel(model: ModelInfo): string {
  const pricing = formatPricing(model.pricing);
  return pricing.length > 0 ? `${model.name} - ${pricing}` : model.name;
}

interface ModelOptionsContext {
  readonly models: readonly ModelInfo[];
  readonly selectedModel: string;
  readonly modelExistsInList: boolean;
  readonly isLoading: boolean;
  readonly isRefreshing: boolean;
}

function renderModelOptions(
  context: ModelOptionsContext,
) {
  const {
    models,
    selectedModel,
    modelExistsInList,
    isLoading,
    isRefreshing,
  } = context;

  if (isLoading) {
    return <option value="">Loading models...</option>;
  }

  if (models.length === 0) {
    return <option value="">No models available</option>;
  }

  return (
    <>
      {selectedModel !== "" && !modelExistsInList && (
        <option value={selectedModel}>{`${selectedModel} (active)`}</option>
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
    </>
  );
}

interface ModelSelectorProps {
  readonly models: readonly ModelInfo[];
  readonly selectedModel: string;
  readonly modelSelectValue: string;
  readonly modelExistsInList: boolean;
  readonly isLoading: boolean;
  readonly isRefreshing: boolean;
  readonly isSetting: boolean;
  readonly error: string | null;
  readonly onModelChange: (event: ChangeEvent<HTMLSelectElement>) => Promise<void>;
}

function ModelSelector({
  models,
  selectedModel,
  modelSelectValue,
  modelExistsInList,
  isLoading,
  isRefreshing,
  isSetting,
  error,
  onModelChange,
}: ModelSelectorProps) {
  const title = error ?? undefined;

  return (
    <div className="relative">
      <label htmlFor="model-select" className="sr-only">
        Select LLM model
      </label>
      <select
        id="model-select"
        value={modelSelectValue}
        onChange={onModelChange}
        disabled={isLoading || isRefreshing || isSetting}
        className="rounded-md border border-border-stronger bg-card px-2 py-1 text-xs text-secondary focus:outline-none focus:ring-2 focus:ring-brand disabled:opacity-50 disabled:cursor-not-allowed"
        aria-label="LLM Model"
        aria-busy={isRefreshing || isSetting}
        title={title}
      >
        {renderModelOptions({
          models,
          selectedModel,
          modelExistsInList,
          isLoading,
          isRefreshing,
        })}
      </select>
      {isRefreshing && <RefreshSpinner />}
    </div>
  );
}

function RefreshSpinner() {
  return (
    <div
      className="absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none"
      aria-hidden="true"
    >
      <svg
        className="animate-spin h-3 w-3 text-secondary"
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
      >
        <circle
          className="opacity-25"
          cx="12"
          cy="12"
          r="10"
          stroke="currentColor"
          strokeWidth="4"
        />
        <path
          className="opacity-75"
          fill="currentColor"
          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
        />
      </svg>
    </div>
  );
}

interface ThemeSelectorProps {
  readonly preference: ThemePreference;
  readonly onThemeChange: (event: ChangeEvent<HTMLSelectElement>) => void;
}

function ThemeSelector({ preference, onThemeChange }: ThemeSelectorProps) {
  return (
    <>
      <label htmlFor="theme-select" className="sr-only">
        Select theme
      </label>
      <select
        id="theme-select"
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
    </>
  );
}

