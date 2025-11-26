import { 
  KBLoadingScreen, 
  KBStatusNotReady, 
  KBHeader, 
  KBQueryForm, 
  KBQueryResults 
} from '.'
import { useKBWorkspace } from '../../hooks/useKBWorkspace'

export function KBWorkspace() {
  const {
    healthStatus,
    isReady,
    isChecking,
    refreshHealth,
    question,
    setQuestion,
    response,
    isLoading,
    submitQuery,
    askFollowUp,
  } = useKBWorkspace()

  if (isChecking) {
    return <KBLoadingScreen />
  }

  if (!isReady) {
    return <KBStatusNotReady healthStatus={healthStatus} onRefresh={refreshHealth} />
  }

  return (
    <div className="max-w-6xl mx-auto p-8">
      <KBHeader healthStatus={healthStatus} onRefresh={refreshHealth} />
      
      <KBQueryForm
        question={question}
        isLoading={isLoading}
        onQuestionChange={setQuestion}
        onSubmit={submitQuery}
        onRefresh={refreshHealth}
      />

      <KBQueryResults response={response} onFollowUp={askFollowUp} />
    </div>
  )
}
