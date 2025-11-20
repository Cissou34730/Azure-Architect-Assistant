import { useState, useEffect } from 'react'

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
  const [activeTab, setActiveTab] = useState<'documents' | 'chat' | 'state' | 'proposal'>('documents')

  useEffect(() => {
    void fetchProjects()
  }, [])

  useEffect(() => {
    if (selectedProject) {
      void fetchProjectState()
      void fetchMessages()
      setTextRequirements(selectedProject.textRequirements || '')
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedProject])

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

    setLoading(true)
    try {
      const response = await fetch(`/api/projects/${selectedProject.id}/analyze-docs`, {
        method: 'POST',
      })

      if (response.ok) {
        const data = await response.json() as { projectState: ProjectState }
        setProjectState(data.projectState)
        setActiveTab('state')
        alert('Documents analyzed successfully!')
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

    setLoading(true)
    const userMessage = chatInput
    setChatInput('')

    try {
      const response = await fetch(`/api/projects/${selectedProject.id}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userMessage }),
      })

      if (response.ok) {
        const data = await response.json() as { message: string; projectState: ProjectState }
        setProjectState(data.projectState)
        await fetchMessages()
      } else {
        const error = await response.json() as { error: string }
        alert(`Error: ${error.error}`)
      }
    } catch (error) {
      console.error('Error sending message:', error)
      alert('Failed to send message')
    } finally {
      setLoading(false)
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
        setProjectState(data.projectState)
      }
    } catch (error) {
      console.error('Error fetching state:', error)
    }
  }

  const generateProposal = async (): Promise<void> => {
    if (!selectedProject) return

    setLoading(true)
    try {
      const response = await fetch(`/api/projects/${selectedProject.id}/architecture/proposal`, {
        method: 'POST',
      })

      if (response.ok) {
        const data = await response.json() as { proposal: string }
        setArchitectureProposal(data.proposal)
        setActiveTab('proposal')
      } else {
        const error = await response.json() as { error: string }
        alert(`Error: ${error.error}`)
      }
    } catch (error) {
      console.error('Error generating proposal:', error)
      alert('Failed to generate proposal')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
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
                        disabled={loading}
                        className="bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700 disabled:opacity-50"
                      >
                        Analyze Requirements
                      </button>
                    </div>
                  )}

                  {activeTab === 'chat' && (
                    <div>
                      <h2 className="text-xl font-semibold mb-4">Clarification Chat</h2>
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
                        />
                        <button
                          type="submit"
                          disabled={loading}
                          className="bg-blue-600 text-white px-6 py-2 rounded-md hover:bg-blue-700 disabled:opacity-50"
                        >
                          Send
                        </button>
                      </form>
                    </div>
                  )}

                  {activeTab === 'state' && (
                    <div>
                      <h2 className="text-xl font-semibold mb-4">Architecture Sheet</h2>
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
                        disabled={loading}
                        className="bg-purple-600 text-white px-4 py-2 rounded-md hover:bg-purple-700 disabled:opacity-50 mb-4"
                      >
                        Generate Proposal
                      </button>
                      {architectureProposal && (
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

      {loading && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
          <div className="bg-white rounded-lg p-6">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
            <p className="mt-4 text-gray-700">Processing...</p>
          </div>
        </div>
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
