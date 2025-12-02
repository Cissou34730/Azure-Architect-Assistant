interface NavigationProps {
  currentView: 'projects' | 'kb' | 'kb-management'
  onViewChange: (view: 'projects' | 'kb' | 'kb-management') => void
}

export function Navigation({ currentView, onViewChange }: NavigationProps) {
  const navItems = [
    { id: 'projects' as const, label: 'Architecture Projects', ariaLabel: 'View architecture projects' },
    { id: 'kb' as const, label: 'Knowledge Base Query', ariaLabel: 'Query knowledge bases' },
    { id: 'kb-management' as const, label: 'KB Management', ariaLabel: 'Manage knowledge bases' },
  ]

  return (
    <nav className="bg-white shadow-sm border-b border-gray-200" role="navigation" aria-label="Main navigation">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <div className="flex space-x-8" role="tablist">
            {navItems.map((item) => (
              <button
                key={item.id}
                onClick={() => onViewChange(item.id)}
                role="tab"
                aria-selected={currentView === item.id ? 'true' : 'false'}
                aria-label={item.ariaLabel}
                className={`px-3 py-2 text-sm font-medium transition-colors ${
                  currentView === item.id
                    ? 'text-accent-primary border-b-2 border-accent-primary'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                {item.label}
              </button>
            ))}
          </div>
          <div className="text-sm text-gray-600" role="banner">
            Azure Architect Assistant
          </div>
        </div>
      </div>
    </nav>
  )
}
