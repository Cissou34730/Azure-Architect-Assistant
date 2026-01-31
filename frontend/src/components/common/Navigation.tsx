import { NavLink } from "react-router-dom";

export function Navigation() {
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

  return (
    <nav
      className="sticky top-0 bg-white shadow-sm border-b border-gray-200 z-40"
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
                      ? "text-blue-600 border-b-2 border-blue-600"
                      : "text-gray-600 hover:text-gray-900"
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </div>
          <div className="text-sm text-gray-600">
            Azure Architect Assistant
          </div>
        </div>
      </div>
    </nav>
  );
}
