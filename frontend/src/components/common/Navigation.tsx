import { NavLink } from "react-router-dom";

export function Navigation() {
  const navItems = [
    {
      to: "/projects",
      label: "Architecture Projects",
      ariaLabel: "View architecture projects",
    },
    {
      to: "/kb",
      label: "Knowledge Base Query",
      ariaLabel: "Query knowledge bases",
    },
    {
      to: "/kb-management",
      label: "KB Management",
      ariaLabel: "Manage knowledge bases",
    },
    {
      to: "/agent-chat",
      label: "Agent Chat",
      ariaLabel: "Chat with Azure Architect Assistant",
    },
  ];

  return (
    <nav
      className="bg-white shadow-sm border-b border-gray-200"
      role="navigation"
      aria-label="Main navigation"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <div className="flex space-x-8" role="tablist">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                role="tab"
                aria-label={item.ariaLabel}
                className={({ isActive }: { isActive: boolean }) =>
                  `px-3 py-2 text-sm font-medium transition-colors ${
                    isActive
                      ? "text-accent-primary border-b-2 border-accent-primary"
                      : "text-gray-600 hover:text-gray-900"
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </div>
          <div className="text-sm text-gray-600" role="banner">
            Azure Architect Assistant
          </div>
        </div>
      </div>
    </nav>
  );
}
