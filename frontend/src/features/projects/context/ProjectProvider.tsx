import type { ProjectContextType } from "./types";
import { projectContextInstance } from "./ProjectContextInstance";

export function ProjectProvider({
  value,
  children,
}: {
  readonly value: ProjectContextType;
  readonly children: React.ReactNode;
}) {
  return (
    <projectContextInstance.Provider value={value}>
      {children}
    </projectContextInstance.Provider>
  );
}
