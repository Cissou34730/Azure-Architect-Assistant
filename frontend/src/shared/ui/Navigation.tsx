import type { ReactNode } from "react";
import { NavLink } from "react-router-dom";
import { workspaceNavigationItems } from "../../app/workspaceRegistry";
interface NavigationProps {
  readonly trailingContent?: ReactNode;
}

export function Navigation({ trailingContent }: NavigationProps) {

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
            {trailingContent}
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
      {workspaceNavigationItems.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          aria-label={item.ariaLabel}
          className={({ isActive }: { isActive: boolean }) =>
            `px-3 py-2 text-sm font-medium transition-colors ${
              isActive ? "text-brand border-b-2 border-brand" : "text-secondary hover:text-foreground"
            }`
          }
        >
          {item.label}
        </NavLink>
      ))}
    </div>
  );
}

