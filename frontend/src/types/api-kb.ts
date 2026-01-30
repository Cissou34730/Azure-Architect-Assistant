export interface KbSource {
  readonly url: string;
  readonly title: string;
  readonly section: string;
  readonly score: number;
  readonly kbId?: string;
  readonly kbName?: string;
}

export interface SendMessageResponse {
  readonly message: string;
  readonly projectState: ProjectState;
  readonly kbSources?: readonly KbSource[];
}

export interface Message {
  readonly id: string;
  readonly projectId: string;
  readonly role: "user" | "assistant";
  readonly content: string;
  readonly timestamp: string;
  readonly kbSources?: readonly KbSource[];
}

export interface KbQueryResponse {
  readonly answer: string;
  readonly sources: readonly KbSource[];
  readonly hasResults: boolean;
  readonly suggestedFollowUps?: readonly string[];
}

export interface KbHealthInfo {
  readonly kbId: string;
  readonly kbName: string;
  readonly status: string;
  readonly indexReady: boolean;
  readonly error?: string;
}

export interface KbInfo {
  readonly id: string;
  readonly name: string;
  readonly status: string;
  readonly profiles: readonly string[];
  readonly priority: number;
  readonly indexReady?: boolean;
}

export interface KbListResponse {
  readonly knowledgeBases: readonly KbInfo[];
}

export interface KbHealthResponse {
  readonly overallStatus: string;
  readonly knowledgeBases: readonly KbHealthInfo[];
}

import type { ProjectState } from "./api-project";
