import type { ReactNode } from "react";
import { NavLink } from "react-router-dom";
import { workspaceNavigationItems } from "../../app/workspaceRegistry";
interface NavigationProps {
  readonly trailingContent?: ReactNode;
}

export function Navigation({ trailingContent }: NavigationProps) {

  return (
    <nav
      className="sticky top-0 bg-card/80 backdrop-blur border-b border-border z-40"
      role="navigation"
      aria-label="Main navigation"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <div className="flex items-center gap-3">
            <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-brand text-inverse font-bold text-sm shadow-sm">
              A
            </span>
            <span className="text-base font-semibold tracking-tight text-foreground">
              Azure Architect Assistant
            </span>
          </div>
          <NavigationLinks />
          <div className="flex items-center gap-3">
            {trailingContent}
          </div>
        </div>
      </div>
    </nav>
  );
}

function NavigationLinks() {
  return (
    <div className="flex items-center gap-1">
      {workspaceNavigationItems.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          aria-label={item.ariaLabel}
          className={({ isActive }: { isActive: boolean }) =>
            `px-3 py-2 text-sm font-medium rounded-md transition-colors ${
              isActive
                ? "bg-brand-soft text-brand-strong"
                : "text-secondary hover:text-foreground hover:bg-surface-muted"
            }`
          }
        >
          {item.label}
        </NavLink>
      ))}
    </div>
  );
}

