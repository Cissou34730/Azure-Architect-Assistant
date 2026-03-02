import { createContext } from "react";
import type { InputAnalysisWorkflowState } from "../hooks/useInputAnalysisWorkflow";

export interface ProjectInputContextType {
  readonly textRequirements: string;
  readonly setTextRequirements: (v: string) => void;
  readonly files: FileList | null;
  readonly setFiles: (f: FileList | null) => void;
  readonly inputWorkflow: InputAnalysisWorkflowState;
  readonly isUploadingDocuments: boolean;
  readonly isAnalyzingDocuments: boolean;
  readonly clearInputWorkflowMessage: () => void;
  readonly handleUploadDocuments: () => Promise<void>;
  readonly handleAnalyzeDocuments: () => Promise<void>;
  readonly handleSaveTextRequirements: () => Promise<void>;
  readonly handleGenerateProposal: () => Promise<void>;
}

export const projectInputContext =
  createContext<ProjectInputContextType | null>(null);
