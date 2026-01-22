/**
 * Types for KB Ingestion API
 */

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

export interface JobMetrics {
  readonly documentsCrawled?: number;
  readonly pagesCrawled?: number;
  readonly pagesTotal?: number;
  readonly documentsCleaned?: number;
  readonly chunksCreated?: number;
  readonly chunksQueued?: number;
  readonly chunksPending?: number;
  readonly chunksProcessing?: number;
  readonly chunksEmbedded?: number;
  readonly chunksFailed?: number;
}

export interface PhaseDetail {
  readonly name: IngestionPhase;
  readonly status: JobStatus;
  readonly progress: number;
  readonly itemsProcessed?: number;
  readonly itemsTotal?: number;
  readonly startedAt?: string | null;
  readonly completedAt?: string | null;
  readonly error?: string | null;
}

export interface IngestionJob {
  readonly jobId: string;
  readonly kbId: string;
  readonly status: JobStatus;
  readonly phase: IngestionPhase;
  readonly progress: number;
  readonly message: string;
  readonly error: string | null;
  readonly metrics: JobMetrics;
  readonly startedAt: string;
  readonly completedAt: string | null;
  readonly phaseDetails?: readonly PhaseDetail[];
}

export interface KnowledgeBase {
  readonly id: string;
  readonly name: string;
  readonly description?: string;
  readonly status: KBStatus;
  readonly sourceType?: SourceType;
  readonly profiles: readonly string[];
  readonly priority: number;
  readonly indexed?: boolean;
  readonly createdAt?: string;
  readonly lastIndexedAt?: string;
}

export interface WebDocumentationConfig {
  readonly startUrls: readonly string[];
  readonly allowedDomains?: readonly string[];
  readonly pathPrefix?: string;
  readonly followLinks?: boolean;
  readonly maxPages?: number;
}

export interface WebGenericConfig {
  readonly urls: readonly string[];
  readonly followLinks?: boolean;
  readonly maxDepth?: number;
  readonly sameDomainOnly?: boolean;
}

export interface PDFSourceConfig {
  readonly files?: readonly string[];
  readonly localPaths?: readonly string[];
  readonly pdfUrls?: readonly string[];
  readonly folderPath?: string;
}

export interface MarkdownSourceConfig {
  readonly files?: readonly string[];
  readonly localPaths?: readonly string[];
  readonly folderPath?: string;
  readonly pdfUrls?: readonly string[];
}

export interface WebsiteSourceConfig {
  readonly url?: string;
  readonly startUrl?: string;
  readonly recursive?: boolean;
  readonly urlPrefix?: string;
  readonly maxPages?: number;
  readonly localPaths?: readonly string[];
}

export interface YoutubeSourceConfig {
  readonly videoUrls?: readonly string[];
  readonly localPaths?: readonly string[];
  readonly pdfUrls?: readonly string[];
}

export type SourceConfig =
  | WebDocumentationConfig
  | WebGenericConfig
  | PDFSourceConfig
  | MarkdownSourceConfig
  | WebsiteSourceConfig
  | YoutubeSourceConfig
  // eslint-disable-next-line @typescript-eslint/no-restricted-types
  | Record<string, unknown>;

export interface CreateKBRequest {
  readonly kbId: string;
  readonly name: string;
  readonly description?: string;
  readonly sourceType: SourceType;
  readonly sourceConfig: SourceConfig;
  readonly embeddingModel?: string;
  readonly chunkSize?: number;
  readonly chunkOverlap?: number;
  readonly profiles?: readonly string[];
  readonly priority?: number;
}

export interface CreateKBResponse {
  readonly message: string;
  readonly kbId: string;
  readonly kbName: string;
}

export interface StartIngestionResponse {
  readonly message: string;
  readonly jobId: string;
  readonly kbId: string;
}

export interface JobListResponse {
  readonly jobs: readonly IngestionJob[];
}

export type KBReadyState = "ready" | "pending" | "paused" | "not_ready";

export interface KBStatusSimple {
  readonly kbId: string;
  readonly status: KBReadyState;
  readonly metrics?: {
    readonly pending?: number;
    readonly processing?: number;
    readonly done?: number;
    readonly error?: number;
  };
}

export interface KBIngestionDetails {
  readonly kbId: string;
  readonly currentPhase: IngestionPhase;
  readonly overallProgress: number;
  readonly phaseDetails: readonly PhaseDetail[];
}
