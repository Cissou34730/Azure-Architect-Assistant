import { useState, useEffect } from 'react'

interface KBSource {
  url: string
  title: string
  section: string
  score: number
  kb_id?: string
  kb_name?: string
}

interface KBQueryResponse {
  answer: string
  sources: KBSource[]
  hasResults: boolean
  suggestedFollowUps?: string[]
}

interface KBHealthInfo {
  kb_id: string
  kb_name: string
  status: string
  index_ready: boolean
  error?: string
}

interface KBHealthResponse {
  overall_status: string
  knowledge_bases: KBHealthInfo[]
}

export function KnowledgeBaseQuery() {
  const [question, setQuestion] = useState('')
  const [response, setResponse] = useState<KBQueryResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [kbsReady, setKbsReady] = useState(false)
  const [healthStatus, setHealthStatus] = useState<KBHealthResponse | null>(null)
  const [checkingStatus, setCheckingStatus] = useState(true)

  useEffect(() => {
    void checkKBHealth()
  }, [])

  const checkKBHealth = async (): Promise<void> => {
    try {
      setCheckingStatus(true)
      const response = await fetch('/api/kb/health')
      
      if (!response.ok) {
        console.error('KB health check failed:', response.status)
        setKbsReady(false)
        setHealthStatus(null)
        return
      }
      
      const data = await response.json() as KBHealthResponse
      setHealthStatus(data)
      
      // Check if at least one KB is ready
      const anyReady = data.knowledge_bases?.some(kb => kb.index_ready) ?? false
      setKbsReady(anyReady)
    } catch (error) {
      console.error('Error checking KB health:', error)
      setKbsReady(false)
      setHealthStatus(null)
    } finally {
      setCheckingStatus(false)
    }
  }



  const submitQuery = async (e: React.FormEvent): Promise<void> => {
    e.preventDefault()
    if (!question.trim()) return

    setLoading(true)
    setResponse(null)

    try {
      const res = await fetch('/api/query/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: question.trim(),
          topKPerKB: 3
        })
      })

      if (res.ok) {
        const data = await res.json() as KBQueryResponse
        setResponse(data)
      } else {
        alert('Failed to query knowledge bases')
      }
    } catch (error) {
      console.error('Error querying knowledge bases:', error)
      alert('Error querying knowledge bases')
    } finally {
      setLoading(false)
    }
  }

  const askFollowUp = (followUpQuestion: string): void => {
    setQuestion(followUpQuestion)
  }

  if (checkingStatus) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Checking knowledge base status...</p>
        </div>
      </div>
    )
  }

  if (!kbsReady) {
    return (
      <div className="max-w-4xl mx-auto p-8">
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 mb-6">
          <h2 className="text-xl font-semibold text-yellow-800 mb-2">
            Knowledge Bases Not Ready
          </h2>
          <p className="text-yellow-700 mb-4">
            No knowledge bases are currently loaded. Status: {healthStatus?.overall_status || 'unknown'}
          </p>
          
          {healthStatus && healthStatus.knowledge_bases && healthStatus.knowledge_bases.length > 0 && (
            <div className="mb-4 space-y-2">
              {healthStatus.knowledge_bases.map(kb => (
                <div key={kb.kb_id} className="flex items-center justify-between bg-white p-3 rounded">
                  <div>
                    <span className="font-medium">{kb.kb_name}</span>
                    <span className="text-sm text-gray-600 ml-2">({kb.kb_id})</span>
                  </div>
                  <div className="flex items-center">
                    <span className={`px-2 py-1 rounded text-sm ${
                      kb.index_ready ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                    }`}>
                      {kb.index_ready ? '✓ Ready' : '✗ Not Ready'}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
          
          <button
            onClick={() => void checkKBHealth()}
            className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700"
          >
            🔄 Refresh Status
          </button>
        </div>

        <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-blue-800 mb-2">
            About Knowledge Base Query System
          </h3>
          <p className="text-blue-700 mb-2">
            This feature allows you to query multiple Azure knowledge bases including:
          </p>
          <ul className="list-disc list-inside text-blue-700 space-y-1">
            <li>Azure Well-Architected Framework</li>
            <li>Cloud Adoption Framework</li>
            <li>Architecture Center patterns and guidance</li>
            <li>Azure service documentation</li>
          </ul>
          <p className="text-blue-600 text-sm mt-4">
            <strong>Note:</strong> Knowledge bases are preloaded at startup. If none are ready, 
            check the server logs or restart the Python service.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-6xl mx-auto p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          Azure Knowledge Base Query
        </h1>
        <p className="text-gray-600">
          Ask questions about Azure best practices, architecture patterns, frameworks, and recommendations
        </p>
        {healthStatus && healthStatus.knowledge_bases && (
          <p className="text-sm text-gray-500 mt-2">
            {healthStatus.knowledge_bases.filter(kb => kb.index_ready).length} of {healthStatus.knowledge_bases.length} knowledge bases ready
          </p>
        )}
      </div>

      {/* Query Form */}
      <form onSubmit={(e) => void submitQuery(e)} className="mb-8">
        <div className="bg-white rounded-lg shadow-md p-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Your Question
          </label>
          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="E.g., What are the best practices for securing Azure SQL databases?"
            rows={3}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            disabled={loading}
          />
          <div className="flex justify-between items-center mt-4">
            <button
              type="submit"
              disabled={loading || !question.trim()}
              className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center"
            >
              {loading ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  Searching...
                </>
              ) : (
                'Search Knowledge Bases'
              )}
            </button>
            <button
              type="button"
              onClick={() => void checkKBHealth()}
              className="text-gray-600 hover:text-gray-800"
            >
              🔄 Refresh Status
            </button>
          </div>
        </div>
      </form>

      {/* Response */}
      {response && (
        <div className="space-y-6">
          {/* Answer */}
          <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Answer</h2>
            <div className="prose prose-blue max-w-none">
              <p className="text-gray-800 whitespace-pre-wrap">{response.answer}</p>
            </div>
          </div>

          {/* Sources */}
          {response.sources && response.sources.length > 0 && (
            <div className="bg-white rounded-lg shadow-md p-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">
                Sources ({response.sources.length})
              </h2>
              <div className="space-y-3">
                {response.sources.map((source, idx) => (
                  <div
                    key={idx}
                    className="border border-gray-200 rounded-lg p-4 hover:border-blue-300 transition-colors"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <a
                          href={source.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-blue-600 hover:text-blue-800 font-medium"
                        >
                          {source.title}
                        </a>
                        <div className="flex items-center gap-3 mt-1">
                          {source.kb_name && (
                            <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded font-medium">
                              {source.kb_name}
                            </span>
                          )}
                          <span className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded">
                            {source.section}
                          </span>
                          <span className="text-xs text-gray-500">
                            Relevance: {(source.score * 100).toFixed(1)}%
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Suggested Follow-ups */}
          {response.suggestedFollowUps && response.suggestedFollowUps.length > 0 && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
              <h2 className="text-lg font-semibold text-blue-900 mb-3">
                Suggested Follow-up Questions
              </h2>
              <div className="space-y-2">
                {response.suggestedFollowUps.map((followUp, idx) => (
                  <button
                    key={idx}
                    onClick={() => askFollowUp(followUp)}
                    className="block w-full text-left px-4 py-2 bg-white border border-blue-200 rounded-lg hover:bg-blue-50 hover:border-blue-300 transition-colors"
                  >
                    <span className="text-blue-700">💬 {followUp}</span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* No Results */}
      {response && !response.hasResults && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
          <p className="text-yellow-800">
            No relevant information found. Try rephrasing your question or being more specific.
          </p>
        </div>
      )}
    </div>
  )
}
