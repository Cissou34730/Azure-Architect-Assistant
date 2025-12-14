import { useState } from 'react'
import { Navigation, Banner, ToastContainer } from './components/common'
import { ProjectWorkspace } from './components/projects'
import { KBWorkspace } from './components/kb'
import { IngestionWorkspace } from './components/ingestion/IngestionWorkspace'
import { useToast } from './hooks/useToast'

function App() {
  const [currentView, setCurrentView] = useState<'projects' | 'kb' | 'kb-management'>('projects')
  const { toasts, close } = useToast()

  return (
    <div className="min-h-screen bg-gray-50">
      <Banner />
      <Navigation currentView={currentView} onViewChange={setCurrentView} />
      
      <main role="main" aria-label={`${currentView} workspace`}>
        {currentView === 'kb-management' ? (
          <IngestionWorkspace />
        ) : currentView === 'kb' ? (
          <KBWorkspace />
        ) : (
          <ProjectWorkspace />
        )}
      </main>
      
      <ToastContainer toasts={toasts} onClose={close} />
    </div>
  )
}

export default App
