import { useState } from 'react'
import { Navigation } from './components/common'
import { ProjectWorkspace } from './components/projects'
import { KBWorkspace } from './components/kb'
import { IngestionWorkspace } from './components/ingestion/IngestionWorkspace'

function App() {
  const [currentView, setCurrentView] = useState<'projects' | 'kb' | 'kb-management'>('projects')

  return (
    <div className="min-h-screen bg-gray-50">
      <Navigation currentView={currentView} onViewChange={setCurrentView} />
      
      {currentView === 'kb-management' ? (
        <IngestionWorkspace />
      ) : currentView === 'kb' ? (
        <KBWorkspace />
      ) : (
        <ProjectWorkspace />
      )}
    </div>
  )
}

export default App
