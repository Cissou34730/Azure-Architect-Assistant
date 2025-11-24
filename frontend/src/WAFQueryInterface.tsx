import { useState, useEffect } from 'react'

interface WAFSource {
  url: string
  title: string
  section: string
  score: number
}

interface WAFQueryResponse {
  answer: string
  sources: WAFSource[]
  scores: number[]
  hasResults: boolean
  discussionEnabled?: boolean
  suggestedFollowUps?: string[]
}

interface WAFStatus {
  stage: string
  progress: number
  message: string
  isComplete: boolean
  error?: string
}

export function WAFQueryInterface() {
  const [question, setQuestion] = useState('')
  const [response, setResponse] = useState<WAFQueryResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [indexReady, setIndexReady] = useState(false)
  const [status, setStatus] = useState<WAFStatus | null>(null)
  const [checkingStatus, setCheckingStatus] = useState(true)

  useEffect(() => {
    void checkIndexStatus()
  }, [])

  const checkIndexStatus = async (): Promise<void> => {
    try {
      setCheckingStatus(true)
      const readyResponse = await fetch('/api/waf/ready')
      const readyData = await readyResponse.json() as { ready: boolean }
      setIndexReady(readyData.ready)

      const statusResponse = await fetch('/api/waf/status')
      const statusData = await statusResponse.json() as WAFStatus
      setStatus(statusData)
    } catch (error) {
      console.error('Error checking WAF status:', error)
    } finally {
      setCheckingStatus(false)
    }
  }

  const startIngestion = async (): Promise<void> => {
    try {
      setLoading(true)
      const response = await fetch('/api/waf/ingest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      })

      if (response.ok) {
        alert('WAF ingestion started. This will take several minutes. Refresh the page to check status.')
      } else {
        alert('Failed to start ingestion')
      }
    } catch (error) {
      console.error('Error starting ingestion:', error)
      alert('Error starting ingestion')
    } finally {
      setLoading(false)
    }
  }

  const submitQuery = async (e: React.FormEvent): Promise<void> => {
    e.preventDefault()
    if (!question.trim()) return

    setLoading(true)
    setResponse(null)

    try {
      const res = await fetch('/api/waf/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: question.trim(),
          topK: 5
        })
      })

      if (res.ok) {
        const data = await res.json() as WAFQueryResponse
        setResponse(data)
      } else {
        alert('Failed to query WAF documentation')
      }
    } catch (error) {
      console.error('Error querying WAF:', error)
      alert('Error querying WAF documentation')
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
          <p className="text-gray-600">Checking WAF status...</p>
        </div>
      </div>
    )
  }

  if (!indexReady) {
    return (
      <div className="max-w-4xl mx-auto p-8">
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 mb-6">
          <h2 className="text-xl font-semibold text-yellow-800 mb-2">
            WAF Index Not Ready
          </h2>
          <p className="text-yellow-700 mb-4">
            {status?.message || 'The WAF documentation index has not been built yet.'}
          </p>
          {status && !status.isComplete && (
            <div className="mb-4">
              <div className="flex justify-between text-sm mb-1">
                <span className="text-yellow-700">Progress: {status.stage}</span>
                <span className="text-yellow-700">{status.progress}%</span>
              </div>
              <div className="w-full bg-yellow-200 rounded-full h-2">
                <div
                  className="bg-yellow-600 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${status.progress}%` } as React.CSSProperties}
                ></div>
              </div>
            </div>
          )}
          <button
            onClick={() => void startIngestion()}
            disabled={loading}
            className="bg-yellow-600 text-white px-6 py-2 rounded-lg hover:bg-yellow-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
          >
            {loading ? 'Starting...' : 'Start WAF Ingestion'}
          </button>
          <button
            onClick={() => void checkIndexStatus()}
            className="ml-4 bg-gray-200 text-gray-700 px-6 py-2 rounded-lg hover:bg-gray-300"
          >
            Refresh Status
          </button>
        </div>

        <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-blue-800 mb-2">
            About WAF Query System
          </h3>
          <p className="text-blue-700 mb-2">
            This feature allows you to query the Azure Well-Architected Framework documentation
            using natural language questions. The system will:
          </p>
          <ul className="list-disc list-inside text-blue-700 space-y-1">
            <li>Crawl and process WAF documentation</li>
            <li>Build a searchable vector index</li>
            <li>Provide source-grounded answers to your questions</li>
            <li>Include relevant documentation links</li>
          </ul>
          <p className="text-blue-600 text-sm mt-4">
            <strong>Note:</strong> The initial ingestion process takes 15-30 minutes and requires
            an OpenAI API key to be configured.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-6xl mx-auto p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          Azure Well-Architected Framework Query
        </h1>
        <p className="text-gray-600">
          Ask questions about Azure best practices, architecture patterns, and recommendations
        </p>
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
                'Search WAF Documentation'
              )}
            </button>
            <button
              type="button"
              onClick={() => void checkIndexStatus()}
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
