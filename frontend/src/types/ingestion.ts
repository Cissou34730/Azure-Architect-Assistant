/**
 * Types for KB Ingestion API
 */

// Enums for better type safety
export type JobStatus =
  | "not_started"
  | "pending"
  | "running"
  | "paused"
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
  return [
    "not_started",
    "pending",
    "running",
    "paused",
    "completed",
    "failed",
  ].includes(value);
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
  readonly phase_details?: readonly PhaseDetail[];
}

export interface PhaseDetail {
  readonly name: IngestionPhase;
  readonly status: JobStatus;
  readonly progress: number;
  readonly items_processed?: number;
  readonly items_total?: number;
  readonly started_at?: string | null;
  readonly completed_at?: string | null;
  readonly error?: string | null;
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

export interface PDFSourceConfig {
  files?: readonly string[];
  local_paths?: string[];
  pdf_urls?: string[];
}

export interface MarkdownSourceConfig {
  files?: readonly string[];
  local_paths?: string[];
  folder_path?: string;
  pdf_urls?: string[]; // Added because wizard might access it on union
}

export interface WebsiteSourceConfig {
  url?: string; // used by some
  start_url?: string; // used by wizard
  recursive?: boolean;
  sitemap_url?: string;
  url_prefix?: string;
  max_pages?: number;
  local_paths?: string[]; // Added because wizard might access it on union
}

export interface YoutubeSourceConfig {
  video_urls?: readonly string[];
  local_paths?: string[]; // Added for consistency
  pdf_urls?: string[]; // Added for consistency
}

export type SourceConfig =
  | WebDocumentationConfig
  | WebGenericConfig
  | PDFSourceConfig
  | MarkdownSourceConfig
  | WebsiteSourceConfig
  | YoutubeSourceConfig
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

// Phase 3: KB-level status (ready | pending | paused | not_ready)
export type KBReadyState = "ready" | "pending" | "paused" | "not_ready";

export interface KBStatusSimple {
  readonly kb_id: string;
  readonly status: KBReadyState;
  readonly metrics?: {
    readonly pending?: number;
    readonly processing?: number;
    readonly done?: number;
    readonly error?: number;
  };
}

// Phase 3: Persisted ingestion details
export interface KBIngestionDetails {
  readonly kb_id: string;
  readonly current_phase: IngestionPhase;
  readonly overall_progress: number;
  readonly phase_details: readonly PhaseDetail[];
}
