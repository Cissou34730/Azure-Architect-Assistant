import type { ProjectState } from '../../types/agent'

interface ProjectStatePanelProps {
  selectedProjectId: string
  projectState: ProjectState | null
  isLoading: boolean
}

export function ProjectStatePanel({ selectedProjectId, projectState, isLoading }: ProjectStatePanelProps) {
  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 flex flex-col h-[calc(100vh-260px)]">
      <div className="px-4 py-3 border-b border-gray-200 bg-gray-50">
        <h2 className="text-lg font-semibold text-gray-900">Project State</h2>
      </div>
      
      <div className="flex-1 overflow-y-auto p-4">
        {!selectedProjectId ? (
          <EmptyState />
        ) : isLoading ? (
          <LoadingState />
        ) : !projectState ? (
          <LoadingState />
        ) : (
          <ProjectStateContent projectState={projectState} />
        )}
      </div>
    </div>
  )
}

function EmptyState() {
  return (
    <div className="text-center text-gray-500 mt-12">
      <div className="text-6xl mb-4">📋</div>
      <h3 className="text-xl font-semibold mb-2">No Project Selected</h3>
      <p className="text-sm">
        Select a project from the dropdown above to view its architecture state.
      </p>
    </div>
  )
}

function LoadingState() {
  return (
    <div className="text-center text-gray-500 mt-12">
      <div className="text-6xl mb-4">⏳</div>
      <h3 className="text-xl font-semibold mb-2">Loading Project State...</h3>
      <p className="text-sm">
        Please wait while we fetch the project information.
      </p>
    </div>
  )
}

function ProjectStateContent({ projectState }: { projectState: ProjectState }) {
  return (
    <div className="space-y-6">
      {/* Context */}
      {projectState.context && (
        <StateSection icon="📝" title="Context">
          {projectState.context.summary && (
            <StateField label="Summary">
              <p className="text-gray-600 mt-1">{projectState.context.summary}</p>
            </StateField>
          )}
          {projectState.context.objectives && projectState.context.objectives.length > 0 && (
            <StateField label="Objectives">
              <ul className="list-disc list-inside text-gray-600 mt-1">
                {projectState.context.objectives.map((obj, i) => (
                  <li key={i}>{obj}</li>
                ))}
              </ul>
            </StateField>
          )}
          {projectState.context.targetUsers && (
            <StateField label="Target Users">
              <p className="text-gray-600 mt-1">{projectState.context.targetUsers}</p>
            </StateField>
          )}
          {projectState.context.scenarioType && (
            <StateField label="Scenario">
              <p className="text-gray-600 mt-1">{projectState.context.scenarioType}</p>
            </StateField>
          )}
        </StateSection>
      )}

      {/* NFRs */}
      {projectState.nfrs && (
        <StateSection icon="🎯" title="Non-Functional Requirements">
          {projectState.nfrs.availability && (
            <StateField label="Availability">
              <p className="text-gray-600 mt-1">{projectState.nfrs.availability}</p>
            </StateField>
          )}
          {projectState.nfrs.security && (
            <StateField label="Security">
              <p className="text-gray-600 mt-1">{projectState.nfrs.security}</p>
            </StateField>
          )}
          {projectState.nfrs.performance && (
            <StateField label="Performance">
              <p className="text-gray-600 mt-1">{projectState.nfrs.performance}</p>
            </StateField>
          )}
          {projectState.nfrs.costConstraints && (
            <StateField label="Cost">
              <p className="text-gray-600 mt-1">{projectState.nfrs.costConstraints}</p>
            </StateField>
          )}
        </StateSection>
      )}

      {/* Application Structure */}
      {projectState.applicationStructure && (
        <StateSection icon="🏗️" title="Application Structure">
          {projectState.applicationStructure.components && projectState.applicationStructure.components.length > 0 && (
            <StateField label="Components">
              <ul className="space-y-1 mt-1">
                {projectState.applicationStructure.components.map((comp, i) => (
                  <li key={i} className="text-gray-600">
                    <span className="font-medium">{comp.name}:</span> {comp.description}
                  </li>
                ))}
              </ul>
            </StateField>
          )}
          {projectState.applicationStructure.integrations && projectState.applicationStructure.integrations.length > 0 && (
            <StateField label="Integrations">
              <p className="text-gray-600 mt-1">{projectState.applicationStructure.integrations.join(', ')}</p>
            </StateField>
          )}
        </StateSection>
      )}

      {/* Open Questions */}
      {projectState.openQuestions && projectState.openQuestions.length > 0 && (
        <StateSection icon="❓" title="Open Questions">
          <div className="bg-yellow-50 rounded-lg p-3">
            <ul className="list-disc list-inside text-sm text-gray-700 space-y-1">
              {projectState.openQuestions.map((q, i) => (
                <li key={i}>{q}</li>
              ))}
            </ul>
          </div>
        </StateSection>
      )}

      {/* Metadata */}
      {projectState.lastUpdated && (
        <div className="text-xs text-gray-500 text-right">
          Last updated: {new Date(projectState.lastUpdated).toLocaleString()}
        </div>
      )}
    </div>
  )
}

function StateSection({ icon, title, children }: { icon: string; title: string; children: React.ReactNode }) {
  return (
    <div>
      <h3 className="text-sm font-semibold text-gray-900 mb-2 flex items-center">
        <span className="mr-2">{icon}</span> {title}
      </h3>
      <div className="bg-gray-50 rounded-lg p-3 space-y-2 text-sm">
        {children}
      </div>
    </div>
  )
}

function StateField({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <span className="font-medium text-gray-700">{label}:</span>
      {children}
    </div>
  )
}
