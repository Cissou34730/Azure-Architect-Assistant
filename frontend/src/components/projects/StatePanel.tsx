import { ProjectState } from '../../services/apiService';

interface StatePanelProps {
  projectState: ProjectState | null;
  onRefreshState: () => void;
  loading: boolean;
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-gray-50 p-4 rounded-md border border-gray-200">
      <h3 className="font-semibold text-lg mb-2">{title}</h3>
      <div className="space-y-2 text-sm">{children}</div>
    </div>
  );
}

export function StatePanel({ projectState, onRefreshState, loading }: StatePanelProps) {
  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-semibold">Architecture Sheet</h2>
        <button
          onClick={onRefreshState}
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
              {projectState.context.objectives.map((obj: any, i: number) => (
                <li key={i}>
                  {typeof obj === 'string' ? obj : (
                    <>
                      <strong>{obj.name}:</strong> {obj.description}
                    </>
                  )}
                </li>
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
              {projectState.applicationStructure.components.map((comp: any, i: number) => (
                <li key={i}>
                  {typeof comp === 'string' ? comp : (
                    <>
                      <strong>{comp.name}:</strong> {comp.description}
                    </>
                  )}
                </li>
              ))}
            </ul>
            <p><strong>Integrations:</strong></p>
            <ul className="list-disc list-inside">
              {projectState.applicationStructure.integrations.map((int: any, i: number) => (
                <li key={i}>
                  {typeof int === 'string' ? int : (
                    <>
                      <strong>{int.name}:</strong> {int.description}
                    </>
                  )}
                </li>
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
              {projectState.technicalConstraints.constraints.map((c: any, i: number) => (
                <li key={i}>
                  {typeof c === 'string' ? c : (
                    <>
                      <strong>{c.name}:</strong> {c.description}
                    </>
                  )}
                </li>
              ))}
            </ul>
            <p><strong>Assumptions:</strong></p>
            <ul className="list-disc list-inside">
              {projectState.technicalConstraints.assumptions.map((a: any, i: number) => (
                <li key={i}>
                  {typeof a === 'string' ? a : (
                    <>
                      <strong>{a.name}:</strong> {a.description}
                    </>
                  )}
                </li>
              ))}
            </ul>
          </Section>

          <Section title="Open Questions">
            <ul className="list-disc list-inside">
              {(projectState.openQuestions || []).map((q: any, i: number) => (
                <li key={i}>
                  {typeof q === 'string' ? q : (
                    <>
                      <strong>{q.name}:</strong> {q.description}
                    </>
                  )}
                </li>
              ))}
            </ul>
          </Section>
        </div>
      ) : (
        <p className="text-gray-500">No architecture sheet available. Please analyze documents first.</p>
      )}
    </div>
  );
}
