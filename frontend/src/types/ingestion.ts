/**
 * Types for KB Ingestion API
 */

export type JobStatus =
  | "PENDING"
  | "RUNNING"
  | "COMPLETED"
  | "FAILED"
  | "CANCELLED";
export type IngestionPhase =
  | "PENDING"
  | "CRAWLING"
  | "CLEANING"
  | "EMBEDDING"
  | "INDEXING"
  | "COMPLETED"
  | "FAILED";
export type SourceType = "website" | "youtube" | "pdf" | "markdown";

export interface JobMetrics {
  pages_crawled?: number;
  pages_total?: number;
  documents_cleaned?: number;
  chunks_created?: number;
  chunks_embedded?: number;
}

export interface IngestionJob {
  job_id: string;
  kb_id: string;
  status: JobStatus;
  phase: IngestionPhase;
  progress: number;
  message: string;
  error: string | null;
  metrics: JobMetrics;
  started_at: string;
  completed_at: string | null;
}

export interface KnowledgeBase {
  id: string;
  name: string;
  description?: string;
  status: string;
  source_type?: SourceType;
  profiles: string[];
  priority: number;
  indexed?: boolean;
  created_at?: string;
  last_indexed_at?: string;
}

export interface WebDocumentationConfig {
  start_urls: string[];
  allowed_domains?: string[];
  path_prefix?: string;
  follow_links?: boolean;
  max_pages?: number;
}

export interface WebGenericConfig {
  urls: string[];
  follow_links?: boolean;
  max_depth?: number;
  same_domain_only?: boolean;
}

export interface CreateKBRequest {
  kb_id: string;
  name: string;
  description?: string;
  source_type: SourceType;
  source_config:
    | WebDocumentationConfig
    | WebGenericConfig
    | Record<string, any>;
  embedding_model?: string;
  chunk_size?: number;
  chunk_overlap?: number;
  profiles?: string[];
  priority?: number;
}

export interface CreateKBResponse {
  message: string;
  kb_id: string;
  kb_name: string;
}

export interface StartIngestionResponse {
  message: string;
  job_id: string;
  kb_id: string;
}

export interface JobListResponse {
  jobs: IngestionJob[];
}
