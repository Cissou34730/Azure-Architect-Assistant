interface NavigationProps {
  currentView: 'projects' | 'kb' | 'kb-management'
  onViewChange: (view: 'projects' | 'kb' | 'kb-management') => void
}

export function Navigation({ currentView, onViewChange }: NavigationProps) {
  const navItems = [
    { id: 'projects' as const, label: 'Architecture Projects' },
    { id: 'kb' as const, label: 'Knowledge Base Query' },
    { id: 'kb-management' as const, label: 'KB Management' },
  ]

  return (
    <nav className="bg-white shadow-sm border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <div className="flex space-x-8">
            {navItems.map((item) => (
              <button
                key={item.id}
                onClick={() => onViewChange(item.id)}
                className={`px-3 py-2 text-sm font-medium ${
                  currentView === item.id
                    ? 'text-blue-600 border-b-2 border-blue-600'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                {item.label}
              </button>
            ))}
          </div>
          <div className="text-sm text-gray-600">
            Azure Architect Assistant
          </div>
        </div>
      </div>
    </nav>
  )
}
