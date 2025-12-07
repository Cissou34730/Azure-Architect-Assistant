import { useState, useEffect, useRef } from 'react'

interface Message {
  role: 'user' | 'assistant'
  content: string
  reasoningSteps?: ReasoningStep[]
}

interface ReasoningStep {
  action: string
  action_input: string
  observation: string
}

interface AgentResponse {
  answer: string
  success: boolean
  reasoning_steps: ReasoningStep[]
  project_state?: ProjectState
  error?: string
}

interface Project {
  id: string
  name: string
  textRequirements: string
  createdAt: string
}

interface ProjectState {
  projectId?: string
  lastUpdated?: string
  context?: {
    summary?: string
    objectives?: string[]
    targetUsers?: string
    scenarioType?: string
  }
  nfrs?: {
    availability?: string
    security?: string
    performance?: string
    costConstraints?: string
  }
  applicationStructure?: {
    components?: Array<{ name: string; description: string }>
    integrations?: string[]
  }
  dataCompliance?: {
    dataTypes?: string[]
    complianceRequirements?: string[]
    dataResidency?: string
  }
  technicalConstraints?: {
    constraints?: string[]
    assumptions?: string[]
  }
  openQuestions?: string[]
}

export function AgentChatWorkspace() {
  const [projects, setProjects] = useState<Project[]>([])
  const [selectedProjectId, setSelectedProjectId] = useState<string>('')
  const [projectState, setProjectState] = useState<ProjectState | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [showReasoning, setShowReasoning] = useState(false)
  const [agentStatus, setAgentStatus] = useState<'unknown' | 'healthy' | 'not_initialized'>('unknown')
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Define functions before useEffect hooks
  const loadProjects = async () => {
    try {
      const response = await fetch('http://localhost:8080/api/projects')
      const data = await response.json()
      setProjects(data.projects || [])
    } catch (error) {
      console.error('Failed to load projects:', error)
    }
  }

  const loadProjectState = async () => {
    if (!selectedProjectId) return
    
    try {
      const response = await fetch(`http://localhost:8080/api/projects/${selectedProjectId}/state`)
      const data = await response.json()
      setProjectState(data.projectState)
    } catch (error) {
      console.error('Failed to load project state:', error)
      setProjectState(null)
    }
  }

  const checkAgentHealth = async () => {
    try {
      const response = await fetch('http://localhost:8080/api/agent/health')
      const data = await response.json()
      setAgentStatus(data.status)
    } catch (error) {
      console.error('Failed to check agent health:', error)
      setAgentStatus('not_initialized')
    }
  }

  const sendMessage = async () => {
    if (!input.trim() || isLoading) return

    const userMessage: Message = { role: 'user', content: input }
    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsLoading(true)

    try {
      // Use project-aware endpoint if project selected, otherwise generic endpoint
      const endpoint = selectedProjectId 
        ? `http://localhost:8080/api/agent/projects/${selectedProjectId}/chat`
        : 'http://localhost:8080/api/agent/chat'
      
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: input }),
      })

      const data: AgentResponse = await response.json()

      const assistantMessage: Message = {
        role: 'assistant',
        content: data.answer,
        reasoningSteps: data.reasoning_steps,
      }

      setMessages(prev => [...prev, assistantMessage])
      
      // Update project state if returned
      if (data.project_state) {
        setProjectState(data.project_state)
      }
    } catch (error) {
      const errorMessage: Message = {
        role: 'assistant',
        content: `Error: ${error instanceof Error ? error.message : 'Failed to get response from agent'}`,
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      void sendMessage()
    }
  }

  const clearChat = () => {
    setMessages([])
  }

  // useEffect hooks after function definitions
  useEffect(() => {
    void checkAgentHealth()
    void loadProjects()
  }, [])

  useEffect(() => {
    if (selectedProjectId) {
      void loadProjectState()
    } else {
      setProjectState(null)
    }
  }, [selectedProjectId, loadProjectState])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  return (
    <div className="max-w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
      {/* Header with Project Selection */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Azure Architect Assistant</h1>
            <p className="mt-1 text-gray-600">
              Chat with the ReAct agent powered by Microsoft documentation
            </p>
          </div>
          <div className="flex items-center space-x-4">
            <div className={`px-3 py-1 rounded-full text-sm font-medium ${
              agentStatus === 'healthy' ? 'bg-green-100 text-green-800' :
              agentStatus === 'not_initialized' ? 'bg-yellow-100 text-yellow-800' :
              'bg-gray-100 text-gray-800'
            }`}>
              {agentStatus === 'healthy' ? '● Ready' :
               agentStatus === 'not_initialized' ? '○ Not Initialized' :
               '○ Unknown'}
            </div>
            <button
              onClick={clearChat}
              className="px-4 py-2 text-sm text-gray-700 hover:text-gray-900 hover:bg-gray-100 rounded-md transition-colors"
            >
              Clear Chat
            </button>
            <button
              onClick={() => setShowReasoning(!showReasoning)}
              className={`px-4 py-2 text-sm rounded-md transition-colors ${
                showReasoning
                  ? 'bg-accent-primary text-white'
                  : 'text-gray-700 hover:bg-gray-100'
              }`}
            >
              {showReasoning ? 'Hide' : 'Show'} Reasoning
            </button>
          </div>
        </div>

        {/* Project Selection Dropdown */}
        <div className="flex items-center space-x-3">
          <label htmlFor="project-select" className="text-sm font-medium text-gray-700">
            Project Context:
          </label>
          <select
            id="project-select"
            value={selectedProjectId}
            onChange={(e) => {
              setSelectedProjectId(e.target.value)
              setMessages([]) // Clear chat when switching projects
            }}
            className="flex-1 max-w-md rounded-lg border border-gray-300 px-4 py-2 focus:outline-none focus:ring-2 focus:ring-accent-primary focus:border-transparent"
          >
            <option value="">No project (Generic mode)</option>
            {projects.map((project) => (
              <option key={project.id} value={project.id}>
                {project.name}
              </option>
            ))}
          </select>
          {selectedProjectId && (
            <span className="text-sm text-gray-500">
              Agent will consider project context in responses
            </span>
          )}
        </div>
      </div>

      {/* Split View: Agent Chat + Project State */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: Agent Chat */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 flex flex-col h-[calc(100vh-260px)]">
          <div className="px-4 py-3 border-b border-gray-200 bg-gray-50">
            <h2 className="text-lg font-semibold text-gray-900">Agent Chat</h2>
          </div>
          
          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.length === 0 ? (
              <div className="text-center text-gray-500 mt-12">
                <div className="text-6xl mb-4">💬</div>
                <h3 className="text-xl font-semibold mb-2">Start a conversation</h3>
                <p className="text-sm mb-4">
                  {selectedProjectId 
                    ? 'Ask about your project architecture, requirements, or get Azure recommendations.'
                    : 'Select a project above for context-aware assistance, or ask generic Azure questions.'}
                </p>
                <div className="mt-6 space-y-2 text-left max-w-lg mx-auto">
                  <p className="text-sm font-medium text-gray-700">Try asking:</p>
                  <ul className="text-sm text-gray-600 space-y-1">
                    {selectedProjectId ? (
                      <>
                        <li>• "We need 99.9% availability"</li>
                        <li>• "What security measures should we implement?"</li>
                        <li>• "How do we handle data residency requirements?"</li>
                      </>
                    ) : (
                      <>
                        <li>• "How do I secure Azure SQL Database?"</li>
                        <li>• "What's the best way to implement microservices?"</li>
                        <li>• "Show me Private Link configuration examples"</li>
                      </>
                    )}
                  </ul>
                </div>
              </div>
            ) : (
              messages.map((message, index) => (
                <div
                  key={index}
                  className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-[85%] rounded-lg px-4 py-3 ${
                      message.role === 'user'
                        ? 'bg-accent-primary text-white'
                        : 'bg-gray-100 text-gray-900'
                    }`}
                  >
                    <div className="whitespace-pre-wrap text-sm">{message.content}</div>
                    
                    {/* Reasoning Steps */}
                    {message.role === 'assistant' && showReasoning && message.reasoningSteps && message.reasoningSteps.length > 0 && (
                      <div className="mt-4 pt-4 border-t border-gray-300">
                        <p className="text-xs font-semibold text-gray-700 mb-2">Reasoning Steps:</p>
                        <div className="space-y-2">
                          {message.reasoningSteps.map((step, stepIndex) => (
                            <div key={stepIndex} className="text-xs bg-white rounded p-2 border border-gray-200">
                              <p className="font-semibold text-gray-800">Action: {step.action}</p>
                              <p className="text-gray-600 mt-1">Input: {step.action_input}</p>
                              <p className="text-gray-600 mt-1">Result: {step.observation.substring(0, 100)}...</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ))
            )}
            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-gray-100 rounded-lg px-4 py-3">
                  <div className="flex items-center space-x-2">
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:0ms]"></div>
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:150ms]"></div>
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:300ms]"></div>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Area */}
          <div className="border-t border-gray-200 p-4">
            <div className="flex space-x-3">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder={selectedProjectId 
                  ? "Ask about your project or specify requirements..."
                  : "Ask about Azure architecture, security, or best practices..."}
                rows={2}
                disabled={isLoading}
                className="flex-1 resize-none rounded-lg border border-gray-300 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-accent-primary focus:border-transparent disabled:bg-gray-50 disabled:text-gray-500"
              />
              <button
                onClick={sendMessage}
                disabled={isLoading || !input.trim()}
                className="px-6 py-3 bg-accent-primary text-white rounded-lg hover:bg-accent-dark disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
              >
                Send
              </button>
            </div>
            <p className="text-xs text-gray-500 mt-2">
              Press Enter to send, Shift+Enter for new line
            </p>
          </div>
        </div>

        {/* Right: Project State */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 flex flex-col h-[calc(100vh-260px)]">
          <div className="px-4 py-3 border-b border-gray-200 bg-gray-50">
            <h2 className="text-lg font-semibold text-gray-900">Project State</h2>
          </div>
          
          <div className="flex-1 overflow-y-auto p-4">
            {!selectedProjectId ? (
              <div className="text-center text-gray-500 mt-12">
                <div className="text-6xl mb-4">📋</div>
                <h3 className="text-xl font-semibold mb-2">No Project Selected</h3>
                <p className="text-sm">
                  Select a project from the dropdown above to view its architecture state.
                </p>
              </div>
            ) : !projectState ? (
              <div className="text-center text-gray-500 mt-12">
                <div className="text-6xl mb-4">⏳</div>
                <h3 className="text-xl font-semibold mb-2">Loading Project State...</h3>
                <p className="text-sm">
                  Please wait while we fetch the project information.
                </p>
              </div>
            ) : (
              <div className="space-y-6">
                {/* Context */}
                {projectState.context && (
                  <div>
                    <h3 className="text-sm font-semibold text-gray-900 mb-2 flex items-center">
                      <span className="mr-2">📝</span> Context
                    </h3>
                    <div className="bg-gray-50 rounded-lg p-3 space-y-2 text-sm">
                      {projectState.context.summary && (
                        <div>
                          <span className="font-medium text-gray-700">Summary:</span>
                          <p className="text-gray-600 mt-1">{projectState.context.summary}</p>
                        </div>
                      )}
                      {projectState.context.objectives && projectState.context.objectives.length > 0 && (
                        <div>
                          <span className="font-medium text-gray-700">Objectives:</span>
                          <ul className="list-disc list-inside text-gray-600 mt-1">
                            {projectState.context.objectives.map((obj, i) => (
                              <li key={i}>{obj}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                      {projectState.context.targetUsers && (
                        <div>
                          <span className="font-medium text-gray-700">Target Users:</span>
                          <p className="text-gray-600 mt-1">{projectState.context.targetUsers}</p>
                        </div>
                      )}
                      {projectState.context.scenarioType && (
                        <div>
                          <span className="font-medium text-gray-700">Scenario:</span>
                          <p className="text-gray-600 mt-1">{projectState.context.scenarioType}</p>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* NFRs */}
                {projectState.nfrs && (
                  <div>
                    <h3 className="text-sm font-semibold text-gray-900 mb-2 flex items-center">
                      <span className="mr-2">🎯</span> Non-Functional Requirements
                    </h3>
                    <div className="bg-gray-50 rounded-lg p-3 space-y-2 text-sm">
                      {projectState.nfrs.availability && (
                        <div>
                          <span className="font-medium text-gray-700">Availability:</span>
                          <p className="text-gray-600 mt-1">{projectState.nfrs.availability}</p>
                        </div>
                      )}
                      {projectState.nfrs.security && (
                        <div>
                          <span className="font-medium text-gray-700">Security:</span>
                          <p className="text-gray-600 mt-1">{projectState.nfrs.security}</p>
                        </div>
                      )}
                      {projectState.nfrs.performance && (
                        <div>
                          <span className="font-medium text-gray-700">Performance:</span>
                          <p className="text-gray-600 mt-1">{projectState.nfrs.performance}</p>
                        </div>
                      )}
                      {projectState.nfrs.costConstraints && (
                        <div>
                          <span className="font-medium text-gray-700">Cost:</span>
                          <p className="text-gray-600 mt-1">{projectState.nfrs.costConstraints}</p>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Application Structure */}
                {projectState.applicationStructure && (
                  <div>
                    <h3 className="text-sm font-semibold text-gray-900 mb-2 flex items-center">
                      <span className="mr-2">🏗️</span> Application Structure
                    </h3>
                    <div className="bg-gray-50 rounded-lg p-3 space-y-2 text-sm">
                      {projectState.applicationStructure.components && projectState.applicationStructure.components.length > 0 && (
                        <div>
                          <span className="font-medium text-gray-700">Components:</span>
                          <ul className="space-y-1 mt-1">
                            {projectState.applicationStructure.components.map((comp, i) => (
                              <li key={i} className="text-gray-600">
                                <span className="font-medium">{comp.name}:</span> {comp.description}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                      {projectState.applicationStructure.integrations && projectState.applicationStructure.integrations.length > 0 && (
                        <div>
                          <span className="font-medium text-gray-700">Integrations:</span>
                          <p className="text-gray-600 mt-1">{projectState.applicationStructure.integrations.join(', ')}</p>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Open Questions */}
                {projectState.openQuestions && projectState.openQuestions.length > 0 && (
                  <div>
                    <h3 className="text-sm font-semibold text-gray-900 mb-2 flex items-center">
                      <span className="mr-2">❓</span> Open Questions
                    </h3>
                    <div className="bg-yellow-50 rounded-lg p-3">
                      <ul className="list-disc list-inside text-sm text-gray-700 space-y-1">
                        {projectState.openQuestions.map((q, i) => (
                          <li key={i}>{q}</li>
                        ))}
                      </ul>
                    </div>
                  </div>
                )}

                {/* Metadata */}
                {projectState.lastUpdated && (
                  <div className="text-xs text-gray-500 text-right">
                    Last updated: {new Date(projectState.lastUpdated).toLocaleString()}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
