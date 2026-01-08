import { useParams, Outlet } from "react-router-dom";
import { useProjectDetails } from "../hooks/useProjectDetails";
import { TabNavigation } from "../../../components/common";
import { ProjectProvider } from "../context/ProjectContext";
import { getTabs } from "../tabs";

export default function ProjectDetailPage() {
  const { projectId } = useParams();
  const projectDetails = useProjectDetails(projectId);
  const { selectedProject, loading, activeTab, setActiveTab } = projectDetails;

  if (!selectedProject && loading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!selectedProject) {
    return (
      <div className="container mx-auto p-6 text-center">
        <h2 className="text-xl font-semibold text-gray-800">
          Project not found
        </h2>
        <p className="text-gray-600 mt-2">
          The requested project could not be found.
        </p>
      </div>
    );
  }

  const tabs = getTabs();

  return (
    <ProjectProvider value={projectDetails}>
      <div className="container mx-auto p-6">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900">
            {selectedProject.name}
          </h1>
          <p className="text-sm text-gray-500">
            Project ID: {selectedProject.id}
          </p>
        </div>

        <div className="bg-white rounded-lg shadow">
          <TabNavigation
            tabs={tabs}
            activeTab={activeTab}
            onTabChange={(tabId: string) => {
              // setActiveTab now navigates
              setActiveTab(tabId);
            }}
          />

          <div className="p-6">
            <Outlet />
          </div>
        </div>
      </div>
    </ProjectProvider>
  );
}
