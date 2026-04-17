import type { JsonObject } from "../../../shared/lib/json";

export type PendingChangeStatus =
  | "pending"
  | "approved"
  | "rejected"
  | "superseded";

export interface PendingChangeSummary {
  readonly id: string;
  readonly projectId: string;
  readonly stage: string;
  readonly status: PendingChangeStatus;
  readonly createdAt: string;
  readonly sourceMessageId: string | null;
  readonly bundleSummary: string;
  readonly artifactCount: number;
}

export interface PendingChangeArtifactDraft {
  readonly id: string;
  readonly artifactType: string;
  readonly artifactId: string | null;
  readonly content: JsonObject;
  readonly citations: readonly JsonObject[];
  readonly createdAt: string | null;
}

export interface PendingChangeDetail extends PendingChangeSummary {
  readonly proposedPatch: JsonObject;
  readonly artifactDrafts: readonly PendingChangeArtifactDraft[];
  readonly citations: readonly JsonObject[];
  readonly reviewedAt: string | null;
  readonly reviewReason: string | null;
}
