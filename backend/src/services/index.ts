/**
 * Services Index
 * Central export point for all services
 */

export { llmService } from "./LLMService.js";
export { chatService } from "./ChatService.js";
export { proposalService } from "./ProposalService.js";
export { openaiClient } from "./OpenAIClient.js";
export { storage } from "./StorageService.js";
export { kbService } from "./KBService.js";
export { ragService } from "./RAGService.js";

// Legacy export for backward compatibility
export { kbService as wafService } from "./KBService.js";

// Type exports
export type {
  KBQueryRequest,
  KBSource,
  KBQueryResponse,
  KBInfo,
  KBHealthResponse,
  QueryProfile,
} from "./KBService.js";

export type { RAGContext, RAGResult } from "./RAGService.js";

export type {
  LLMResponse,
  ProgressCallback,
  KBSource as Source,
} from "./types.js";
