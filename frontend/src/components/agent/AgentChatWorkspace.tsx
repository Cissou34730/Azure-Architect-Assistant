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
  error?: string
}

export function AgentChatWorkspace() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [showReasoning, setShowReasoning] = useState(false)
  const [agentStatus, setAgentStatus] = useState<'unknown' | 'healthy' | 'not_initialized'>('unknown')
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    checkAgentHealth()
  }, [])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

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
      const response = await fetch('http://localhost:8080/api/agent/chat', {
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
      sendMessage()
    }
  }

  const clearChat = () => {
    setMessages([])
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Azure Architect Assistant</h1>
            <p className="mt-2 text-gray-600">
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
      </div>

      {/* Chat Area */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 flex flex-col h-[calc(100vh-280px)]">
        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {messages.length === 0 ? (
            <div className="text-center text-gray-500 mt-12">
              <div className="text-6xl mb-4">💬</div>
              <h3 className="text-xl font-semibold mb-2">Start a conversation</h3>
              <p className="text-sm">
                Ask me about Azure architecture, security best practices, or service recommendations.
              </p>
              <div className="mt-6 space-y-2 text-left max-w-2xl mx-auto">
                <p className="text-sm font-medium text-gray-700">Try asking:</p>
                <ul className="text-sm text-gray-600 space-y-1">
                  <li>• "How do I secure Azure SQL Database?"</li>
                  <li>• "What's the best way to implement microservices on Azure?"</li>
                  <li>• "Show me how to configure Private Link for Azure services"</li>
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
                  className={`max-w-3xl rounded-lg px-4 py-3 ${
                    message.role === 'user'
                      ? 'bg-accent-primary text-white'
                      : 'bg-gray-100 text-gray-900'
                  }`}
                >
                  <div className="whitespace-pre-wrap">{message.content}</div>
                  
                  {/* Reasoning Steps */}
                  {message.role === 'assistant' && showReasoning && message.reasoningSteps && message.reasoningSteps.length > 0 && (
                    <div className="mt-4 pt-4 border-t border-gray-300">
                      <p className="text-xs font-semibold text-gray-700 mb-2">Reasoning Steps:</p>
                      <div className="space-y-2">
                        {message.reasoningSteps.map((step, stepIndex) => (
                          <div key={stepIndex} className="text-xs bg-white rounded p-2 border border-gray-200">
                            <p className="font-semibold text-gray-800">Action: {step.action}</p>
                            <p className="text-gray-600 mt-1">Input: {step.action_input}</p>
                            <p className="text-gray-600 mt-1">Result: {step.observation.substring(0, 150)}...</p>
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
              placeholder="Ask about Azure architecture, security, or best practices..."
              rows={2}
              disabled={isLoading}
              className="flex-1 resize-none rounded-lg border border-gray-300 px-4 py-3 focus:outline-none focus:ring-2 focus:ring-accent-primary focus:border-transparent disabled:bg-gray-50 disabled:text-gray-500"
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
    </div>
  )
}
