import { describe, it, expect } from "vitest";
import { useProjectLoading } from "../../../../features/projects/hooks/useProjectLoading";

describe("useProjectLoading", () => {
  it("returns false when all flags are false", () => {
    const result = useProjectLoading({
      loadingProject: false,
      loadingState: false,
      loadingChat: false,
      loadingProposal: false,
    });
    expect(result).toBe(false);
  });

  it("returns true when loadingProject is true", () => {
    const result = useProjectLoading({
      loadingProject: true,
      loadingState: false,
      loadingChat: false,
      loadingProposal: false,
    });
    expect(result).toBe(true);
  });

  it("returns true when loadingState is true", () => {
    const result = useProjectLoading({
      loadingProject: false,
      loadingState: true,
      loadingChat: false,
      loadingProposal: false,
    });
    expect(result).toBe(true);
  });

  it("returns true when loadingChat is true", () => {
    const result = useProjectLoading({
      loadingProject: false,
      loadingState: false,
      loadingChat: true,
      loadingProposal: false,
    });
    expect(result).toBe(true);
  });

  it("returns true when loadingProposal is true", () => {
    const result = useProjectLoading({
      loadingProject: false,
      loadingState: false,
      loadingChat: false,
      loadingProposal: true,
    });
    expect(result).toBe(true);
  });

  it("returns true when multiple flags are true", () => {
    const result = useProjectLoading({
      loadingProject: true,
      loadingState: true,
      loadingChat: false,
      loadingProposal: false,
    });
    expect(result).toBe(true);
  });
});
