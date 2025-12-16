import { useState, useEffect } from 'react'

type AgentStatus = 'unknown' | 'healthy' | 'not_initialized'

export function useAgentHealth() {
  const [agentStatus, setAgentStatus] = useState<AgentStatus>('unknown')

  const checkHealth = async () => {
    try {
      const response = await fetch('http://localhost:8080/api/agent/health')
      const data = await response.json()
      setAgentStatus(data.status)
    } catch (error) {
      console.error('Failed to check agent health:', error)
      setAgentStatus('not_initialized')
    }
  }

  useEffect(() => {
    void checkHealth()
  }, [])

  return { agentStatus, refreshHealth: checkHealth }
}
