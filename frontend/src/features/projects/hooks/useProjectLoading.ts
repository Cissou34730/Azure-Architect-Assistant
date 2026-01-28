interface ProjectLoadingStates {
  readonly loadingProject: boolean;
  readonly loadingState: boolean;
  readonly loadingChat: boolean;
  readonly loadingProposal: boolean;
}

export function useProjectLoading({
  loadingProject,
  loadingState,
  loadingChat,
  loadingProposal,
}: ProjectLoadingStates) {
  return loadingProject || loadingState || loadingChat || loadingProposal;
}
