export interface ProjectTraceEvent {
  readonly id: string;
  readonly projectId: string;
  readonly threadId: string | null;
  readonly eventType: string;
  readonly payload: Record<string, unknown>;
  readonly createdAt: string;
}

export interface ProjectTraceEventsResponse {
  readonly events: readonly ProjectTraceEvent[];
}
