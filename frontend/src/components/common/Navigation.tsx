import { NavLink } from "react-router-dom";
import { useTheme, type ThemePreference } from "../../hooks/useTheme";

export function Navigation() {
  const { preference, setPreference } = useTheme();

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

