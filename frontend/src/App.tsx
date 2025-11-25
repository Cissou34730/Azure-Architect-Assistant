import { useState, useEffect } from 'react'
import { KnowledgeBaseQuery } from './KnowledgeBaseQuery.js'
import { useProjects } from './hooks/useProjects'
import { useProjectState } from './hooks/useProjectState'
import { useChat } from './hooks/useChat'
import { useProposal } from './hooks/useProposal'
import { ProjectList } from './components/ProjectList'
import { DocumentsPanel } from './components/DocumentsPanel'
import { ChatPanel } from './components/ChatPanel'
import { StatePanel } from './components/StatePanel'
import { ProposalPanel } from './components/ProposalPanel'

function App() {
  // Use custom hooks
  const {
    projects,
    selectedProject,
    setSelectedProject,
    loading: projectsLoading,
    fetchProjects,
    createProject,
    uploadDocuments,
    saveTextRequirements,
  } = useProjects()

  const {
    projectState,
    loading: stateLoading,
    analyzeDocuments,
    refreshState,
  } = useProjectState(selectedProject?.id ?? null)

  const {
    messages,
    chatInput,
    setChatInput,
    loading: chatLoading,
    loadingMessage: chatLoadingMessage,
    sendMessage,
  } = useChat(selectedProject?.id ?? null)

  const {
    architectureProposal,
    proposalStage,
    loading: proposalLoading,
    generateProposal,
  } = useProposal()

  // Local state for UI
  const [projectName, setProjectName] = useState('')
  const [textRequirements, setTextRequirements] = useState('')
  const [files, setFiles] = useState<FileList | null>(null)
  const [activeTab, setActiveTab] = useState<'documents' | 'chat' | 'state' | 'proposal'>('documents')
  const [currentView, setCurrentView] = useState<'projects' | 'kb'>('projects')

  // Determine overall loading state
  const loading = projectsLoading || stateLoading || chatLoading || proposalLoading
  const loadingMessage = chatLoadingMessage

  // Logging helper
  const logAction = (action: string, details?: any) => {
    const timestamp = new Date().toISOString()
    console.log(`[${timestamp}] ${action}`, details || '')
  }

  useEffect(() => {
    logAction('App initialized')
    void fetchProjects()
  }, [fetchProjects])

  useEffect(() => {
    if (selectedProject) {
      logAction('Project selected', { projectId: selectedProject.id, name: selectedProject.name })
      setTextRequirements(selectedProject.textRequirements || '')
    }
  }, [selectedProject])

  useEffect(() => {
    if (projectState) {
      logAction('Project state changed in UI', { 
        projectId: projectState.projectId,
        lastUpdated: projectState.lastUpdated,
        openQuestionsCount: projectState.openQuestions.length
      })
    }
  }, [projectState])

  // Refresh state when switching to State tab
  useEffect(() => {
    if (activeTab === 'state' && selectedProject) {
      logAction('State tab activated, refreshing project state')
      void refreshState()
    }
  }, [activeTab, selectedProject, refreshState])

  // Handler functions
  const handleCreateProject = async (e: React.FormEvent): Promise<void> => {
    e.preventDefault()
    if (!projectName.trim()) return

    try {
      await createProject(projectName)
      setProjectName('')
    } catch (error) {
      console.error('Error creating project:', error)
    }
  }

  const handleUploadDocuments = async (e: React.FormEvent): Promise<void> => {
    e.preventDefault()
    if (!files || files.length === 0) return

    try {
      await uploadDocuments(files)
      alert('Documents uploaded successfully!')
      setFiles(null)
      const fileInput = document.getElementById('file-input') as HTMLInputElement
      if (fileInput) fileInput.value = ''
    } catch (error) {
      console.error('Error uploading documents:', error)
    }
  }

  const handleSaveTextRequirements = async (): Promise<void> => {
    try {
      await saveTextRequirements(textRequirements)
      alert('Requirements saved successfully!')
    } catch (error) {
      console.error('Error saving requirements:', error)
    }
  }

  const handleAnalyzeDocuments = async (): Promise<void> => {
    if (!selectedProject) return

    // Check if we have either text requirements or documents
    if (!selectedProject.textRequirements?.trim() && (!files || files.length === 0)) {
      alert('Please provide either text requirements or upload documents before analyzing.')
      return
    }

    try {
      await analyzeDocuments()
      setActiveTab('state')
      alert('Analysis complete!')
    } catch (error: any) {
      alert(`Error: ${error.message || 'Failed to analyze documents'}`)
    }
  }

  const handleSendChatMessage = async (e: React.FormEvent): Promise<void> => {
    e.preventDefault()
    if (!chatInput.trim()) return

    const userMessage = chatInput
    logAction('Sending chat message', { projectId: selectedProject?.id, messagePreview: userMessage.substring(0, 50) })
    
    try {
      await sendMessage(userMessage)
    } catch (error: any) {
      logAction('Chat message failed', { error: error.message })
      alert(`Error: ${error.message}`)
    }
  }

  const handleGenerateProposal = (): void => {
    if (!selectedProject) return
    
    logAction('User initiated proposal generation', { projectId: selectedProject.id })
    generateProposal(selectedProject.id, () => {
      logAction('Proposal generation complete, refreshing state')
      void refreshState()
    })
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Top Navigation */}
      <nav className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex space-x-8">
              <button
                onClick={() => setCurrentView('projects')}
                className={`px-3 py-2 text-sm font-medium ${
                  currentView === 'projects'
                    ? 'text-blue-600 border-b-2 border-blue-600'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                Architecture Projects
              </button>
              <button
                onClick={() => setCurrentView('kb')}
                className={`px-3 py-2 text-sm font-medium ${
                  currentView === 'kb'
                    ? 'text-blue-600 border-b-2 border-blue-600'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                Knowledge Base Query
              </button>
            </div>
            <div className="text-sm text-gray-600">
              Azure Architect Assistant
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      {currentView === 'kb' ? (
        <KnowledgeBaseQuery />
      ) : (
        <>
          <div className="bg-blue-600 text-white p-4 shadow-lg">
            <h1 className="text-2xl font-bold">Azure Architecture Assistant - POC</h1>
          </div>

          <div className="container mx-auto p-6">
            <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
              <div className="lg:col-span-1">
                <ProjectList
                  projects={projects}
                  selectedProject={selectedProject}
                  onSelectProject={setSelectedProject}
                  projectName={projectName}
                  onProjectNameChange={setProjectName}
                  onCreateProject={handleCreateProject}
                  loading={loading}
                />
              </div>

              <div className="lg:col-span-3">
                {selectedProject ? (
                  <div className="bg-white rounded-lg shadow">
                    <div className="border-b border-gray-200">
                      <nav className="flex space-x-4 px-6 pt-4">
                        {(['documents', 'chat', 'state', 'proposal'] as const).map((tab) => (
                          <button
                            key={tab}
                            onClick={() => setActiveTab(tab)}
                            className={`px-4 py-2 text-sm font-medium rounded-t-lg ${
                              activeTab === tab
                                ? 'bg-blue-600 text-white'
                                : 'text-gray-600 hover:text-gray-800'
                            }`}
                          >
                            {tab.charAt(0).toUpperCase() + tab.slice(1)}
                          </button>
                        ))}
                      </nav>
                    </div>

                    <div className="p-6">
                      {activeTab === 'documents' && (
                        <DocumentsPanel
                          selectedProject={selectedProject}
                          textRequirements={textRequirements}
                          onTextRequirementsChange={setTextRequirements}
                          onSaveTextRequirements={handleSaveTextRequirements}
                          files={files}
                          onFilesChange={setFiles}
                          onUploadDocuments={handleUploadDocuments}
                          onAnalyzeDocuments={handleAnalyzeDocuments}
                          loading={loading}
                          loadingMessage={loadingMessage}
                        />
                      )}

                      {activeTab === 'chat' && (
                        <ChatPanel
                          messages={messages}
                          chatInput={chatInput}
                          onChatInputChange={setChatInput}
                          onSendMessage={handleSendChatMessage}
                          loading={loading}
                          loadingMessage={loadingMessage}
                        />
                      )}

                      {activeTab === 'state' && (
                        <StatePanel
                          projectState={projectState}
                          onRefreshState={refreshState}
                          loading={loading}
                        />
                      )}

                      {activeTab === 'proposal' && (
                        <ProposalPanel
                          architectureProposal={architectureProposal}
                          proposalStage={proposalStage}
                          onGenerateProposal={handleGenerateProposal}
                          loading={loading}
                        />
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="bg-white rounded-lg shadow p-8 text-center">
                    <p className="text-gray-500 text-lg">Select or create a project to get started</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

export default App
