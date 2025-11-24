import { useState, useEffect, useRef } from 'react'
import { WAFQueryInterface } from './WAFQueryInterface.js'

interface Project {
  id: string
  name: string
  textRequirements?: string
  createdAt: string
}

interface ProjectState {
  projectId: string
  context: {
    summary: string
    objectives: string[]
    targetUsers: string
    scenarioType: string
  }
  nfrs: {
    availability: string
    security: string
    performance: string
    costConstraints: string
  }
  applicationStructure: {
    components: string[]
    integrations: string[]
  }
  dataCompliance: {
    dataTypes: string[]
    complianceRequirements: string[]
    dataResidency: string
  }
  technicalConstraints: {
    constraints: string[]
    assumptions: string[]
  }
  openQuestions: string[]
  lastUpdated: string
}

interface Message {
  id: string
  projectId: string
  role: 'user' | 'assistant'
  content: string
  timestamp: string
  wafSources?: WAFSource[]
}

interface WAFSource {
  url: string
  title: string
  section: string
  score: number
}

function App() {
  const [projects, setProjects] = useState<Project[]>([])
  const [selectedProject, setSelectedProject] = useState<Project | null>(null)
  const [projectName, setProjectName] = useState('')
  const [textRequirements, setTextRequirements] = useState('')
  const [files, setFiles] = useState<FileList | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [chatInput, setChatInput] = useState('')
  const [projectState, setProjectState] = useState<ProjectState | null>(null)
  const [architectureProposal, setArchitectureProposal] = useState<string>('')
  const [loading, setLoading] = useState(false)
  const [loadingMessage, setLoadingMessage] = useState<string>('')
  const [proposalStage, setProposalStage] = useState<string>('')
  const [activeTab, setActiveTab] = useState<'documents' | 'chat' | 'state' | 'proposal'>('documents')
  const [currentView, setCurrentView] = useState<'projects' | 'waf'>('projects')
  const proposalTimers = useRef<NodeJS.Timeout[]>([])

  // Logging helper
  const logAction = (action: string, details?: any) => {
    const timestamp = new Date().toISOString()
    console.log(`[${timestamp}] ${action}`, details || '')
  }

  useEffect(() => {
    logAction('App initialized')
    void fetchProjects()
  }, [])

  useEffect(() => {
    if (selectedProject) {
      logAction('Project selected', { projectId: selectedProject.id, name: selectedProject.name })
      void fetchProjectState()
      void fetchMessages()
      setTextRequirements(selectedProject.textRequirements || '')
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
      void fetchProjectState()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab])

  const fetchProjects = async (): Promise<void> => {
    try {
      const response = await fetch('/api/projects')
      const data = await response.json() as { projects: Project[] }
      setProjects(data.projects)
    } catch (error) {
      console.error('Error fetching projects:', error)
    }
  }

  const createProject = async (e: React.FormEvent): Promise<void> => {
    e.preventDefault()
    if (!projectName.trim()) return

    setLoading(true)
    try {
      const response = await fetch('/api/projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: projectName }),
      })

      if (response.ok) {
        const data = await response.json() as { project: Project }
        setProjects([...projects, data.project])
        setSelectedProject(data.project)
        setProjectName('')
      }
    } catch (error) {
      console.error('Error creating project:', error)
    } finally {
      setLoading(false)
    }
  }

  const uploadDocuments = async (e: React.FormEvent): Promise<void> => {
    e.preventDefault()
    if (!selectedProject || !files || files.length === 0) return

    setLoading(true)
    try {
      const formData = new FormData()
      Array.from(files).forEach((file) => {
        formData.append('files', file)
      })

      const response = await fetch(`/api/projects/${selectedProject.id}/documents`, {
        method: 'POST',
        body: formData,
      })

      if (response.ok) {
        alert('Documents uploaded successfully!')
        setFiles(null)
        const fileInput = document.getElementById('file-input') as HTMLInputElement
        if (fileInput) fileInput.value = ''
      }
    } catch (error) {
      console.error('Error uploading documents:', error)
    } finally {
      setLoading(false)
    }
  }

  const saveTextRequirements = async (): Promise<void> => {
    if (!selectedProject) return

    setLoading(true)
    try {
      const response = await fetch(`/api/projects/${selectedProject.id}/requirements`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ textRequirements }),
      })

      if (response.ok) {
        const data = await response.json() as { project: Project }
        setSelectedProject(data.project)
        setProjects(projects.map(p => p.id === data.project.id ? data.project : p))
        alert('Requirements saved successfully!')
      }
    } catch (error) {
      console.error('Error saving requirements:', error)
    } finally {
      setLoading(false)
    }
  }

  const analyzeDocuments = async (): Promise<void> => {
    if (!selectedProject) return

    // Check if we have either text requirements or documents
    if (!selectedProject.textRequirements?.trim() && (!files || files.length === 0)) {
      alert('Please provide either text requirements or upload documents before analyzing.')
      return
    }

    setLoading(true)
    try {
      const response = await fetch(`/api/projects/${selectedProject.id}/analyze-docs`, {
        method: 'POST',
      })

      if (response.ok) {
        const data = await response.json() as { projectState: ProjectState }
        setProjectState(data.projectState)
        setActiveTab('state')
        alert('Analysis complete!')
      } else {
        const error = await response.json() as { error: string }
        alert(`Error: ${error.error}`)
      }
    } catch (error) {
      console.error('Error analyzing documents:', error)
      alert('Failed to analyze documents')
    } finally {
      setLoading(false)
    }
  }

  const sendChatMessage = async (e: React.FormEvent): Promise<void> => {
    e.preventDefault()
    if (!selectedProject || !chatInput.trim()) return

    const userMessage = chatInput
    logAction('Sending chat message', { projectId: selectedProject.id, messagePreview: userMessage.substring(0, 50) })
    setLoading(true)
    setLoadingMessage('Processing your question (checking WAF documentation)...')
    setChatInput('')

    try {
      const response = await fetch(`/api/projects/${selectedProject.id}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userMessage }),
      })

      if (response.ok) {
        const data = await response.json() as { 
          message: string
          projectState: ProjectState
          wafSources?: WAFSource[]
        }
        logAction('Chat message processed', { 
          hasWafSources: Boolean(data.wafSources && data.wafSources.length > 0),
          sourceCount: data.wafSources?.length || 0,
          stateUpdated: Boolean(data.projectState)
        })
        
        // Update project state - force re-render by creating new object
        if (data.projectState) {
          setProjectState({ ...data.projectState })
          logAction('Architecture sheet updated', { 
            lastUpdated: data.projectState.lastUpdated,
            openQuestions: data.projectState.openQuestions.length
          })
        }
        
        // Fetch messages to get the complete conversation including WAF sources
        await fetchMessages()
      } else {
        const error = await response.json() as { error: string }
        logAction('Chat message failed', { error: error.error })
        alert(`Error: ${error.error}`)
      }
    } catch (error) {
      logAction('Chat message error', error)
      console.error('Error sending message:', error)
      alert('Failed to send message')
    } finally {
      setLoading(false)
      setLoadingMessage('')
    }
  }

  const fetchMessages = async (): Promise<void> => {
    if (!selectedProject) return

    try {
      const response = await fetch(`/api/projects/${selectedProject.id}/messages`)
      const data = await response.json() as { messages: Message[] }
      setMessages(data.messages)
    } catch (error) {
      console.error('Error fetching messages:', error)
    }
  }

  const fetchProjectState = async (): Promise<void> => {
    if (!selectedProject) return

    try {
      const response = await fetch(`/api/projects/${selectedProject.id}/state`)
      if (response.ok) {
        const data = await response.json() as { projectState: ProjectState }
        logAction('Fetched project state', { 
          hasState: Boolean(data.projectState),
          lastUpdated: data.projectState?.lastUpdated
        })
        setProjectState(data.projectState)
      } else {
        logAction('Failed to fetch project state', { status: response.status })
      }
    } catch (error) {
      logAction('Error fetching project state', error)
      console.error('Error fetching state:', error)
    }
  }

  const generateProposal = (): void => {
    if (!selectedProject) return

    logAction('Generating architecture proposal', { projectId: selectedProject.id })
    setLoading(true)
    setProposalStage('Starting proposal generation...')
    
    const url = `/api/projects/${selectedProject.id}/architecture/proposal`
    logAction('Opening SSE connection', { url })
    
    // Create EventSource connection (backend handles it as POST)
    const eventSource = new EventSource(url)
    
    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        logAction('SSE message received', data)
        
        if (data.stage === 'done') {
          // Proposal complete
          setArchitectureProposal(data.proposal)
          setProposalStage('Refreshing architecture sheet...')
          
          // Close the connection
          eventSource.close()
          
          // Refresh state
          fetchProjectState().then(() => {
            logAction('State refresh complete after proposal')
            setProposalStage('')
            setLoading(false)
          }).catch((error) => {
            logAction('Error refreshing state', error)
            setProposalStage('')
            setLoading(false)
          })
        } else if (data.stage === 'error') {
          // Error occurred
          logAction('Proposal generation error from SSE', data)
          alert(`Error: ${data.error}`)
          eventSource.close()
          setProposalStage('')
          setLoading(false)
        } else {
          // Progress update
          const stageMessages: Record<string, string> = {
            'started': 'Initializing...',
            'querying_waf': data.detail || 'Querying Azure Well-Architected Framework...',
            'building_context': 'Building context from WAF guidance...',
            'generating_proposal': 'Generating comprehensive proposal with AI...',
            'finalizing': 'Finalizing proposal...',
            'completed': 'Completed successfully'
          }
          setProposalStage(stageMessages[data.stage] || data.detail || 'Processing...')
        }
      } catch (error) {
        logAction('Error parsing SSE message', error)
      }
    }
    
    eventSource.onerror = (error) => {
      logAction('SSE connection error', error)
      eventSource.close()
      
      alert('Connection error during proposal generation')
      setProposalStage('')
      setLoading(false)
    }
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
                onClick={() => setCurrentView('waf')}
                className={`px-3 py-2 text-sm font-medium ${
                  currentView === 'waf'
                    ? 'text-blue-600 border-b-2 border-blue-600'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                WAF Query
              </button>
            </div>
            <div className="text-sm text-gray-600">
              Azure Architect Assistant
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      {currentView === 'waf' ? (
        <WAFQueryInterface />
      ) : (
        <>
          <div className="bg-blue-600 text-white p-4 shadow-lg">
            <h1 className="text-2xl font-bold">Azure Architecture Assistant - POC</h1>
          </div>

          <div className="container mx-auto p-6">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          <div className="lg:col-span-1">
            <div className="bg-white rounded-lg shadow p-4">
              <h2 className="text-lg font-semibold mb-4">Projects</h2>
              
              <form onSubmit={createProject} className="mb-4">
                <input
                  type="text"
                  value={projectName}
                  onChange={(e) => setProjectName(e.target.value)}
                  placeholder="New project name"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md mb-2 text-sm"
                />
                <button
                  type="submit"
                  disabled={loading}
                  className="w-full bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 disabled:opacity-50 text-sm"
                >
                  Create Project
                </button>
              </form>

              <div className="space-y-2">
                {projects.map((project) => (
                  <button
                    key={project.id}
                    onClick={() => setSelectedProject(project)}
                    className={`w-full text-left px-3 py-2 rounded-md text-sm ${
                      selectedProject?.id === project.id
                        ? 'bg-blue-100 border border-blue-500'
                        : 'bg-gray-50 hover:bg-gray-100'
                    }`}
                  >
                    {project.name}
                  </button>
                ))}
              </div>
            </div>
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
                    <div>
                      <h2 className="text-xl font-semibold mb-4">Documents & Requirements</h2>
                      
                      <div className="mb-6">
                        <h3 className="font-semibold mb-2">Text Requirements</h3>
                        <textarea
                          value={textRequirements}
                          onChange={(e) => setTextRequirements(e.target.value)}
                          placeholder="Describe your project requirements here..."
                          className="w-full px-3 py-2 border border-gray-300 rounded-md mb-2 text-sm"
                          rows={5}
                        />
                        <button
                          onClick={saveTextRequirements}
                          disabled={loading}
                          className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 disabled:opacity-50 mb-4"
                        >
                          Save Requirements
                        </button>
                      </div>
                      
                      <h3 className="font-semibold mb-2">Upload Documents</h3>
                      <form onSubmit={uploadDocuments} className="mb-4">
                        <input
                          id="file-input"
                          type="file"
                          multiple
                          title="Select files to upload"
                          onChange={(e) => setFiles(e.target.files)}
                          className="w-full mb-2"
                        />
                        <button
                          type="submit"
                          disabled={loading || !files}
                          className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 disabled:opacity-50 mr-2"
                        >
                          Upload Documents
                        </button>
                      </form>
                      <button
                        onClick={analyzeDocuments}
                        disabled={loading || (!textRequirements.trim() && !selectedProject.textRequirements?.trim())}
                        className="bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700 disabled:opacity-50 flex items-center gap-2"
                      >
                        {loading && loadingMessage.includes('Analyzing') ? (
                          <>
                            <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                            </svg>
                            <span>Analyzing...</span>
                          </>
                        ) : 'Analyze Requirements'}
                      </button>
                      {loading && loadingMessage.includes('Analyzing') && (
                        <p className="text-sm text-blue-600 mt-2">{loadingMessage}</p>
                      )}
                      {!textRequirements.trim() && !selectedProject.textRequirements?.trim() && (
                        <p className="text-sm text-gray-500 mt-2">Please add text requirements or upload documents to enable analysis.</p>
                      )}
                    </div>
                  )}

                  {activeTab === 'chat' && (
                    <div>
                      <h2 className="text-xl font-semibold mb-4">Clarification Chat</h2>
                      {loading && loadingMessage && (
                        <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-md flex items-center gap-2">
                          <svg className="animate-spin h-5 w-5 text-blue-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                          </svg>
                          <span className="text-sm text-blue-800">{loadingMessage}</span>
                        </div>
                      )}
                      <div className="h-96 overflow-y-auto border border-gray-200 rounded-md p-4 mb-4">
                        {messages.map((msg) => (
                          <div
                            key={msg.id}
                            className={`mb-4 ${
                              msg.role === 'user' ? 'text-right' : 'text-left'
                            }`}
                          >
                            <div
                              className={`inline-block max-w-[80%] p-3 rounded-lg ${
                                msg.role === 'user'
                                  ? 'bg-blue-600 text-white'
                                  : 'bg-gray-200 text-gray-800'
                              }`}
                            >
                              <div className="text-xs mb-1 opacity-75">
                                {msg.role === 'user' ? 'You' : 'Assistant'}
                              </div>
                              <div className="whitespace-pre-wrap">{msg.content}</div>
                              {msg.role === 'assistant' && msg.wafSources && msg.wafSources.length > 0 && (
                                <div className="mt-3 pt-3 border-t border-gray-300">
                                  <div className="text-xs font-semibold mb-2">Sources (Azure Well-Architected Framework):</div>
                                  <div className="space-y-1">
                                    {msg.wafSources.map((source, idx) => (
                                      <div key={idx} className="text-xs">
                                        <a
                                          href={source.url}
                                          target="_blank"
                                          rel="noopener noreferrer"
                                          className="text-blue-600 hover:underline"
                                        >
                                          {source.title} ({source.section})
                                        </a>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                      <form onSubmit={sendChatMessage} className="flex gap-2">
                        <input
                          type="text"
                          value={chatInput}
                          onChange={(e) => setChatInput(e.target.value)}
                          placeholder="Ask a question or provide clarification..."
                          className="flex-1 px-3 py-2 border border-gray-300 rounded-md"
                          disabled={loading}
                        />
                        <button
                          type="submit"
                          disabled={loading || !chatInput.trim()}
                          className="bg-blue-600 text-white px-6 py-2 rounded-md hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
                        >
                          {loading ? (
                            <>
                              <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                              </svg>
                              <span>Sending...</span>
                            </>
                          ) : 'Send'}
                        </button>
                      </form>
                    </div>
                  )}

                  {activeTab === 'state' && (
                    <div>
                      <div className="flex justify-between items-center mb-4">
                        <h2 className="text-xl font-semibold">Architecture Sheet</h2>
                        <button
                          onClick={() => void fetchProjectState()}
                          disabled={loading}
                          className="bg-gray-600 text-white px-3 py-1 rounded-md hover:bg-gray-700 disabled:opacity-50 text-sm flex items-center gap-1"
                        >
                          <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                          </svg>
                          Refresh
                        </button>
                      </div>
                      {projectState ? (
                        <div className="space-y-4">
                          <Section title="Context">
                            <p><strong>Summary:</strong> {projectState.context.summary}</p>
                            <p><strong>Target Users:</strong> {projectState.context.targetUsers}</p>
                            <p><strong>Scenario Type:</strong> {projectState.context.scenarioType}</p>
                            <p><strong>Objectives:</strong></p>
                            <ul className="list-disc list-inside">
                              {projectState.context.objectives.map((obj, i) => (
                                <li key={i}>{obj}</li>
                              ))}
                            </ul>
                          </Section>

                          <Section title="Non-Functional Requirements">
                            <p><strong>Availability:</strong> {projectState.nfrs.availability}</p>
                            <p><strong>Security:</strong> {projectState.nfrs.security}</p>
                            <p><strong>Performance:</strong> {projectState.nfrs.performance}</p>
                            <p><strong>Cost:</strong> {projectState.nfrs.costConstraints}</p>
                          </Section>

                          <Section title="Application Structure">
                            <p><strong>Components:</strong></p>
                            <ul className="list-disc list-inside">
                              {projectState.applicationStructure.components.map((comp, i) => (
                                <li key={i}>{comp}</li>
                              ))}
                            </ul>
                            <p><strong>Integrations:</strong></p>
                            <ul className="list-disc list-inside">
                              {projectState.applicationStructure.integrations.map((int, i) => (
                                <li key={i}>{int}</li>
                              ))}
                            </ul>
                          </Section>

                          <Section title="Data & Compliance">
                            <p><strong>Data Types:</strong> {projectState.dataCompliance.dataTypes.join(', ')}</p>
                            <p><strong>Compliance:</strong> {projectState.dataCompliance.complianceRequirements.join(', ')}</p>
                            <p><strong>Data Residency:</strong> {projectState.dataCompliance.dataResidency}</p>
                          </Section>

                          <Section title="Technical Constraints">
                            <p><strong>Constraints:</strong></p>
                            <ul className="list-disc list-inside">
                              {projectState.technicalConstraints.constraints.map((c, i) => (
                                <li key={i}>{c}</li>
                              ))}
                            </ul>
                            <p><strong>Assumptions:</strong></p>
                            <ul className="list-disc list-inside">
                              {projectState.technicalConstraints.assumptions.map((a, i) => (
                                <li key={i}>{a}</li>
                              ))}
                            </ul>
                          </Section>

                          <Section title="Open Questions">
                            <ul className="list-disc list-inside">
                              {projectState.openQuestions.map((q, i) => (
                                <li key={i}>{q}</li>
                              ))}
                            </ul>
                          </Section>
                        </div>
                      ) : (
                        <p className="text-gray-500">No architecture sheet available. Please analyze documents first.</p>
                      )}
                    </div>
                  )}

                  {activeTab === 'proposal' && (
                    <div>
                      <h2 className="text-xl font-semibold mb-4">Azure Architecture Proposal</h2>
                      
                      <button
                        onClick={generateProposal}
                        disabled={loading && proposalStage !== ''}
                        className="bg-purple-600 text-white px-4 py-2 rounded-md hover:bg-purple-700 disabled:opacity-50 mb-4 flex items-center gap-2"
                      >
                        {loading && proposalStage ? 'Generating...' : 'Generate Proposal'}
                      </button>
                      
                      {proposalStage && (
                        <div className="mb-6 p-4 bg-gradient-to-r from-purple-50 to-blue-50 border border-purple-200 rounded-lg">
                          <div className="flex items-start gap-3">
                            <div className="shrink-0 mt-1">
                              <div className="flex space-x-1">
                                <div className="w-2 h-2 bg-purple-600 rounded-full animate-bounce"></div>
                                <div className="w-2 h-2 bg-purple-600 rounded-full animate-bounce" style={{ animationDelay: '0.15s' }}></div>
                                <div className="w-2 h-2 bg-purple-600 rounded-full animate-bounce" style={{ animationDelay: '0.3s' }}></div>
                              </div>
                            </div>
                            <div className="flex-1">
                              <div className="text-sm font-medium text-purple-900 mb-1">Thinking...</div>
                              <div className="text-sm text-purple-700">{proposalStage}</div>
                              <div className="mt-2 text-xs text-purple-600">This may take up to 40 seconds</div>
                            </div>
                          </div>
                        </div>
                      )}
                      
                      {architectureProposal && !proposalStage && (
                        <div className="prose max-w-none">
                          <pre className="whitespace-pre-wrap bg-gray-50 p-4 rounded-md border border-gray-200">
                            {architectureProposal}
                          </pre>
                        </div>
                      )}
                    </div>
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

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-gray-50 p-4 rounded-md border border-gray-200">
      <h3 className="font-semibold text-lg mb-2">{title}</h3>
      <div className="space-y-2 text-sm">{children}</div>
    </div>
  )
}

export default App
