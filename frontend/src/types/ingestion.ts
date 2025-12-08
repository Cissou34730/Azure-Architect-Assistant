/**
 * Types for KB Ingestion API
 */

// Enums for better type safety
export type JobStatus =
  | "not_started"
  | "pending"
  | "running"
  | "completed"
  | "failed";

export type IngestionPhase =
  | "loading"
  | "chunking"
  | "embedding"
  | "indexing"
  | "completed"
  | "failed";

export type SourceType =
  | "web_documentation"
  | "web_generic"
  | "website"
  | "pdf"
  | "markdown"
  | "youtube";

export type KBStatus = "active" | "inactive" | "archived";

// Type guard functions
export const isJobStatus = (value: string): value is JobStatus => {
  return ["not_started", "pending", "running", "completed", "failed"].includes(
    value
  );
};

export const isIngestionPhase = (value: string): value is IngestionPhase => {
  return [
    "loading",
    "chunking",
    "embedding",
    "indexing",
    "completed",
    "failed",
  ].includes(value);
};

export interface JobMetrics {
  // Crawling phase
  readonly documents_crawled?: number;
  readonly pages_crawled?: number;
  readonly pages_total?: number;

  // Chunking phase
  readonly documents_cleaned?: number;
  readonly chunks_created?: number;
  readonly chunks_queued?: number;

  // Queue status
  readonly chunks_pending?: number;
  readonly chunks_processing?: number;
  readonly chunks_embedded?: number;
  readonly chunks_failed?: number;

  // Legacy
  readonly batches_processed?: number;
}

export interface IngestionJob {
  readonly job_id: string;
  readonly kb_id: string;
  readonly status: JobStatus;
  readonly phase: IngestionPhase;
  readonly progress: number;
  readonly message: string;
  readonly error: string | null;
  readonly metrics: JobMetrics;
  readonly started_at: string;
  readonly completed_at: string | null;
}

export interface KnowledgeBase {
  readonly id: string;
  readonly name: string;
  readonly description?: string;
  readonly status: KBStatus;
  readonly source_type?: SourceType;
  readonly profiles: readonly string[];
  readonly priority: number;
  readonly indexed?: boolean;
  readonly created_at?: string;
  readonly last_indexed_at?: string;
}

export interface WebDocumentationConfig {
  start_urls: readonly string[];
  allowed_domains?: readonly string[];
  path_prefix?: string;
  follow_links?: boolean;
  max_pages?: number;
}

export interface WebGenericConfig {
  urls: readonly string[];
  follow_links?: boolean;
  max_depth?: number;
  same_domain_only?: boolean;
}

export type SourceConfig =
  | WebDocumentationConfig
  | WebGenericConfig
  | Record<string, unknown>;

export interface CreateKBRequest {
  kb_id: string;
  name: string;
  description?: string;
  source_type: SourceType;
  source_config: SourceConfig;
  embedding_model?: string;
  chunk_size?: number;
  chunk_overlap?: number;
  profiles?: readonly string[];
  priority?: number;
}

export interface CreateKBResponse {
  readonly message: string;
  readonly kb_id: string;
  readonly kb_name: string;
}

export interface StartIngestionResponse {
  readonly message: string;
  readonly job_id: string;
  readonly kb_id: string;
}

export interface JobListResponse {
  readonly jobs: readonly IngestionJob[];
}

// API Error type
export interface APIError {
  readonly message: string;
  readonly detail?: string;
  readonly status?: number;
}
