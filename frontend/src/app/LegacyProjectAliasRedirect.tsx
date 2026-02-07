import { Navigate, useParams } from "react-router-dom";

export function LegacyProjectAliasRedirect() {
  const { projectId } = useParams<{ projectId: string }>();
  if (projectId === undefined || projectId === "") {
    return <Navigate to="/project" replace />;
  }
  return <Navigate to={`/project/${projectId}`} replace />;
}
