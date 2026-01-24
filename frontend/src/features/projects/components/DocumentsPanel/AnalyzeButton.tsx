import { Project } from "../../../../types/api";

interface AnalyzeButtonProps {
  readonly selectedProject: Project;
  readonly textRequirements: string;
  readonly onAnalyze: () => void;
  readonly loading: boolean;
  readonly loadingMessage: string;
}

export function AnalyzeButton({
  selectedProject,
  textRequirements,
  onAnalyze,
  loading,
  loadingMessage,
}: AnalyzeButtonProps) {
  const isAnalyzing = loading && loadingMessage.includes("Analyzing");
  const hasNoRequirements =
    textRequirements.trim() === "" &&
    (!selectedProject.textRequirements ||
      selectedProject.textRequirements.trim() === "");

  return (
    <>
      <button
        onClick={onAnalyze}
        disabled={loading || hasNoRequirements}
        className="bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700 disabled:opacity-50 flex items-center gap-2"
      >
        {isAnalyzing ? "Analyzing..." : "Analyze Requirements"}
      </button>

      {isAnalyzing && (
        <p className="text-sm text-blue-600 mt-2">{loadingMessage}</p>
      )}

      {hasNoRequirements && (
        <p className="text-sm text-gray-500 mt-2">
          Please add text requirements or upload documents to enable analysis.
        </p>
      )}
    </>
  );
}
