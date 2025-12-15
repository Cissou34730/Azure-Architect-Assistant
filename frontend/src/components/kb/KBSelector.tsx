interface KB {
  id: string
  name: string
  status: string
  profiles: string[]
  index_ready?: boolean
}

interface Props {
  availableKBs: KB[]
  selectedKBs: string[]
  onSelectionChange: (kbIds: string[]) => void
  disabled?: boolean
}

export function KBSelector({ availableKBs, selectedKBs, onSelectionChange, disabled }: Props) {
  const handleToggle = (kbId: string) => {
    if (selectedKBs.includes(kbId)) {
      onSelectionChange(selectedKBs.filter(id => id !== kbId))
    } else {
      onSelectionChange([...selectedKBs, kbId])
    }
  }

  const handleSelectAll = () => {
    const activeKBs = availableKBs
      .filter(kb => kb.status === 'active' && kb.index_ready !== false)
      .map(kb => kb.id)
    onSelectionChange(activeKBs)
  }

  const handleClearAll = () => {
    onSelectionChange([])
  }

  return (
    <div className="bg-white rounded-lg shadow-md p-6 mb-6">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Select Knowledge Bases</h3>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={handleSelectAll}
            disabled={disabled}
            className="text-sm text-blue-600 hover:text-blue-800 disabled:text-gray-400"
          >
            Select All
          </button>
          <span className="text-gray-300">|</span>
          <button
            type="button"
            onClick={handleClearAll}
            disabled={disabled}
            className="text-sm text-blue-600 hover:text-blue-800 disabled:text-gray-400"
          >
            Clear
          </button>
        </div>
      </div>

      <div className="space-y-2">
        {availableKBs.length === 0 ? (
          <p className="text-gray-500 text-sm">No knowledge bases available</p>
        ) : (
          availableKBs.map((kb) => (
            <label
              key={kb.id}
              className={`flex items-center p-3 rounded-lg border cursor-pointer transition-colors ${
                selectedKBs.includes(kb.id)
                  ? 'bg-blue-50 border-blue-300'
                  : 'bg-gray-50 border-gray-200 hover:bg-gray-100'
              } ${(disabled || kb.index_ready === false) ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
              <input
                type="checkbox"
                checked={selectedKBs.includes(kb.id)}
                onChange={() => handleToggle(kb.id)}
                disabled={disabled || kb.status !== 'active' || kb.index_ready === false}
                className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
              />
              <div className="ml-3 flex-1">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-gray-900">{kb.name}</span>
                  <span
                    className={`text-xs px-2 py-1 rounded ${
                      kb.status === 'active' && kb.index_ready !== false
                        ? 'bg-green-100 text-green-800'
                        : 'bg-yellow-100 text-yellow-800'
                    }`}
                  >
                    {kb.index_ready === false ? 'not-indexed' : kb.status}
                  </span>
                </div>
                {kb.profiles.length > 0 && (
                  <div className="flex gap-1 mt-1">
                    {kb.profiles.map((profile) => (
                      <span
                        key={profile}
                        className="text-xs text-gray-600 bg-gray-100 px-2 py-0.5 rounded"
                      >
                        {profile}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </label>
          ))
        )}
      </div>

      {selectedKBs.length > 0 && (
        <div className="mt-3 text-sm text-gray-600">
          {selectedKBs.length} knowledge base{selectedKBs.length !== 1 ? 's' : ''} selected
        </div>
      )}
    </div>
  )
}
