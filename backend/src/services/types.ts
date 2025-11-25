/**
 * Shared types for AI services
 */

import { ProjectState } from "../models/Project.js";

/**
 * Generic source from knowledge bases
 * Compatible with any KB, not just WAF
 */
export interface KBSource {
  url: string;
  title: string;
  section: string;
  score: number;
  kb_id?: string;
  kb_name?: string;
}

/**
 * Response from LLM operations
 */
export interface LLMResponse {
  assistantMessage?: string;
  projectState: ProjectState;
  sources?: KBSource[];
}

/**
 * Progress callback for long-running operations
 */
export type ProgressCallback = (stage: string, detail?: string) => void;

/**
 * OpenAI configuration
 */
export interface OpenAIConfig {
  apiKey: string;
  apiEndpoint: string;
  model: string;
}
