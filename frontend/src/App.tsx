import { useState } from 'react'
import { Navigation, Banner } from './components/common'
import { ProjectWorkspace } from './components/projects'
import { KBWorkspace } from './components/kb'
import { IngestionWorkspace } from './components/ingestion/IngestionWorkspace'
import { AgentChatWorkspace } from './components/agent'

function App() {
  const [currentView, setCurrentView] = useState<'projects' | 'kb' | 'kb-management' | 'agent-chat'>('projects')

  return (
    <div className="min-h-screen bg-gray-50">
      <Banner />
      <Navigation currentView={currentView} onViewChange={setCurrentView} />
      
      <main role="main" aria-label={`${currentView} workspace`}>
        {currentView === 'agent-chat' ? (
          <AgentChatWorkspace />
        ) : currentView === 'kb-management' ? (
          <IngestionWorkspace />
        ) : currentView === 'kb' ? (
          <KBWorkspace />
        ) : (
          <ProjectWorkspace />
        )}
      </main>
    </div>
  )
}

export default App
