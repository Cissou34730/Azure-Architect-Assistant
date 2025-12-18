import { useEffect } from 'react'
import { ProjectList, DocumentsPanel, ChatPanel, StatePanel, ProposalPanel } from '.'
import { TabNavigation } from '../common'
import { DiagramSetViewer } from '../diagrams/DiagramSetViewer'
import { useProjectWorkspace } from '../../hooks/useProjectWorkspace'

export function ProjectWorkspace() {
  const {
    // UI State
    activeTab,
    setActiveTab,
    projectName,
    setProjectName,
    textRequirements,
    setTextRequirements,
    files,
    setFiles,
    loading,
    loadingMessage,

    // Data
    projects,
    selectedProject,
    setSelectedProject,
    projectState,
    messages,
    chatInput,
    setChatInput,
    architectureProposal,
    proposalStage,

    // Handlers
    handleCreateProject,
    handleUploadDocuments,
    handleSaveTextRequirements,
    handleAnalyzeDocuments,
    handleSendChatMessage,
    handleGenerateProposal,
    refreshState,
    fetchProjects,
  } = useProjectWorkspace()

  useEffect(() => {
    void fetchProjects()
  }, [fetchProjects])

  const tabs = [
    { id: 'documents', label: 'Documents' },
    { id: 'chat', label: 'Chat' },
    { id: 'state', label: 'State' },
    { id: 'proposal', label: 'Proposal' },
    { id: 'diagrams', label: 'Diagrams' },
  ]

  return (
    <>
      <div className="bg-blue-600 text-white p-4 shadow-lg">
        <h1 className="text-2xl font-bold">Azure Architecture Assistant - POC</h1>
      </div>

      <div className="container mx-auto p-6">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Sidebar */}
          <div className="lg:col-span-1">
            <ProjectList
              projects={projects}
              selectedProject={selectedProject}
              onSelectProject={setSelectedProject}
              projectName={projectName}
              onProjectNameChange={setProjectName}
              onCreateProject={handleCreateProject}
              loading={loading}
            />
          </div>

          {/* Main Content Area */}
          <div className="lg:col-span-3">
            {selectedProject ? (
              <div className="bg-white rounded-lg shadow">
                <TabNavigation
                  tabs={tabs}
                  activeTab={activeTab}
                  onTabChange={(tabId) => setActiveTab(tabId as 'documents' | 'chat' | 'state' | 'proposal' | 'diagrams')}
                />

                <div className="p-6">
                  {activeTab === 'documents' && (
                    <DocumentsPanel
                      selectedProject={selectedProject}
                      textRequirements={textRequirements}
                      onTextRequirementsChange={setTextRequirements}
                      onSaveTextRequirements={handleSaveTextRequirements}
                      files={files}
                      onFilesChange={setFiles}
                      onUploadDocuments={handleUploadDocuments}
                      onAnalyzeDocuments={handleAnalyzeDocuments}
                      loading={loading}
                      loadingMessage={loadingMessage}
                    />
                  )}

                  {activeTab === 'chat' && (
                    <ChatPanel
                      messages={messages}
                      chatInput={chatInput}
                      onChatInputChange={setChatInput}
                      onSendMessage={handleSendChatMessage}
                      loading={loading}
                      loadingMessage={loadingMessage}
                    />
                  )}

                  {activeTab === 'state' && (
                    <StatePanel
                      projectState={projectState}
                      onRefreshState={refreshState}
                      loading={loading}
                    />
                  )}

                  {activeTab === 'proposal' && (
                    <ProposalPanel
                      architectureProposal={architectureProposal}
                      proposalStage={proposalStage}
                      onGenerateProposal={handleGenerateProposal}
                      loading={loading}
                    />
                  )}

                  {activeTab === 'diagrams' && (
                    <DiagramSetViewer diagramSetId="aa57f645-e736-430e-bab0-e8c6a953a047" />
                  )}
                </div>
              </div>
            ) : (
              <div className="bg-white rounded-lg shadow p-8 text-center">
                <p className="text-gray-500 text-lg">
                  Select or create a project to get started
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  )
}
