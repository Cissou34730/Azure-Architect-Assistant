import { NavLink } from "react-router-dom";
import { useTheme, type ThemePreference } from "../../hooks/useTheme";
import { useModelSelector } from "../../hooks/useModelSelector";
import type { PricingInfo } from "../../services/settingsService";

/**
 * Format pricing information for display in dropdown.
 *
 * @param pricing - Pricing info or null
 * @returns Formatted pricing string (e.g., "$0.01/$0.03")
 */
function formatPricing(pricing: PricingInfo | null): string {
  if (!pricing) {
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
    error,
    refreshModels,
    setModel: setSelectedModel,
  } = useModelSelector();

  const navItems = [
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

  const themeOptions: { value: ThemePreference; label: string }[] = [
    { value: "system", label: "System" },
    { value: "light", label: "Light" },
    { value: "dark", label: "Dark" },
  ];

  return (
    <nav
      className="sticky top-0 bg-card shadow-sm border-b border-border z-40"
      role="navigation"
      aria-label="Main navigation"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-14">
          <div className="flex space-x-8">
            {navItems.map((item) => (
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
          <div className="flex items-center gap-3">
            {/* Model Selector Dropdown */}
            <div className="relative">
              <label htmlFor="model-select" className="sr-only">
                Select LLM model
              </label>
              <select
                id="model-select"
                value={selectedModel}
                onChange={async (event) => {
                  const value = event.target.value;
                  
                  // Handle refresh action
                  if (value === "__refresh__") {
                    try {
                      await refreshModels();
                    } catch (err) {
                      console.error("Failed to refresh models:", err);
                    }
                    return;
                  }
                  
                  // Handle model change
                  try {
                    await setSelectedModel(value);
                  } catch (err) {
                    // Error is already handled by the hook with rollback
                    console.error("Failed to change model:", err);
                  }
                }}
                disabled={isLoading || isRefreshing}
                className="rounded-md border border-border-stronger bg-card px-2 py-1 text-xs text-secondary focus:outline-none focus:ring-2 focus:ring-brand disabled:opacity-50 disabled:cursor-not-allowed"
                aria-label="LLM Model"
                title={error || undefined}
              >
                {isLoading && (
                  <option value="">Loading models...</option>
                )}
                {!isLoading && models.length === 0 && (
                  <option value="">No models available</option>
                )}
                {!isLoading && models.length > 0 && (
                  <>
                    {models.map((model) => {
                      const pricing = formatPricing(model.pricing);
                      const label = pricing
                        ? `${model.name} - ${pricing}`
                        : model.name;
                      return (
                        <option key={model.id} value={model.id}>
                          {label}
                        </option>
                      );
                    })}
                    <option disabled>──────────</option>
                    <option value="__refresh__">
                      {isRefreshing ? "🔄 Refreshing..." : "🔄 Refresh Models"}
                    </option>
                  </>
                )}
              </select>
              {isRefreshing && (
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
              )}
            </div>

            {/* Theme Selector */}
            <label htmlFor="theme-select" className="sr-only">
              Select theme
            </label>
            <select
              id="theme-select"
              value={preference}
              onChange={(event) => setPreference(event.target.value as ThemePreference)}
              className="rounded-md border border-border-stronger bg-card px-2 py-1 text-xs text-secondary focus:outline-none focus:ring-2 focus:ring-brand"
              aria-label="Theme"
            >
              {themeOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
            <div className="text-sm text-secondary">
              Azure Architect Assistant
            </div>
          </div>
        </div>
      </div>
    </nav>
  );
}

