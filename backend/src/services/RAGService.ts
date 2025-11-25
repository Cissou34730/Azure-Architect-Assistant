/**
 * RAG Service
 * High-level service for Retrieval-Augmented Generation operations
 * Provides context-aware KB querying with appropriate profiles
 */

import { logger } from "../logger.js";
import {
  kbService,
  KBQueryResponse,
  KBSource,
  KBHealthResponse,
  KBListResponse,
} from "./KBService.js";

export type RAGContext = "chat" | "analysis" | "proposal";

export interface RAGResult {
  context: string;
  sources: KBSource[];
  hasResults: boolean;
}

/**
 * RAG Service
 * Orchestrates knowledge base queries for different contexts
 */
class RAGService {
  private log = logger.child("RAGService");

  /**
   * Query knowledge bases for chat context (fast, interactive)
   */
  async queryForChat(question: string): Promise<RAGResult> {
    try {
      this.log.info("RAG query for chat", {
        question: question.substring(0, 100),
      });

      const response = await kbService.queryChat(question, 3);

      return {
        context: this.formatContext(response),
        sources: response.sources,
        hasResults: response.hasResults,
      };
    } catch (error) {
      this.log.warn("RAG query for chat failed, returning empty context", {
        error,
      });
      return {
        context: "",
        sources: [],
        hasResults: false,
      };
    }
  }

  /**
   * Query knowledge bases for document analysis (moderate depth)
   */
  async queryForAnalysis(question: string): Promise<RAGResult> {
    try {
      this.log.info("RAG query for analysis", {
        question: question.substring(0, 100),
      });

      // Use chat profile but with more results
      const response = await kbService.queryChat(question, 5);

      return {
        context: this.formatContext(response),
        sources: response.sources,
        hasResults: response.hasResults,
      };
    } catch (error) {
      this.log.warn("RAG query for analysis failed, returning empty context", {
        error,
      });
      return {
        context: "",
        sources: [],
        hasResults: false,
      };
    }
  }

  /**
   * Query knowledge bases for proposal generation (comprehensive)
   */
  async queryForProposal(questions: string[]): Promise<RAGResult> {
    try {
      this.log.info("RAG query for proposal", {
        questionCount: questions.length,
      });

      // Query all questions using proposal profile and merge results
      const responses = await Promise.all(
        questions.map((q) => kbService.queryProposal(q, 5))
      );

      // Merge contexts and deduplicate sources
      const allContexts = responses
        .filter((r) => r.hasResults)
        .map((r) => this.formatContext(r));

      const allSources = this.deduplicateSources(
        responses.flatMap((r) => r.sources)
      );

      const hasResults = responses.some((r) => r.hasResults);

      this.log.info("RAG proposal query completed", {
        contextCount: allContexts.length,
        sourceCount: allSources.length,
      });

      return {
        context: allContexts.join("\n\n---\n\n"),
        sources: allSources,
        hasResults,
      };
    } catch (error) {
      this.log.warn("RAG query for proposal failed, returning empty context", {
        error,
      });
      return {
        context: "",
        sources: [],
        hasResults: false,
      };
    }
  }

  /**
   * Query multiple topics in parallel (for proposal generation)
   */
  async queryMultipleTopics(
    topics: Array<{ topic: string; profile: "chat" | "proposal" }>
  ): Promise<Map<string, RAGResult>> {
    try {
      this.log.info("RAG multi-topic query", { topicCount: topics.length });

      const results = await Promise.allSettled(
        topics.map(async (t) => {
          const response =
            t.profile === "chat"
              ? await kbService.queryChat(t.topic, 3)
              : await kbService.queryProposal(t.topic, 5);

          return {
            topic: t.topic,
            result: {
              context: this.formatContext(response),
              sources: response.sources,
              hasResults: response.hasResults,
            },
          };
        })
      );

      const resultMap = new Map<string, RAGResult>();

      results.forEach((result, index) => {
        if (result.status === "fulfilled") {
          resultMap.set(result.value.topic, result.value.result);
        } else {
          this.log.warn(`Topic ${topics[index].topic} failed`, {
            error: result.reason,
          });
          resultMap.set(topics[index].topic, {
            context: "",
            sources: [],
            hasResults: false,
          });
        }
      });

      return resultMap;
    } catch (error) {
      this.log.error("Multi-topic query failed", { error });
      throw error;
    }
  }

  /**
   * Format KB response into context string
   */
  private formatContext(response: KBQueryResponse): string {
    if (!response.hasResults || response.sources.length === 0) {
      return "";
    }

    const contextParts: string[] = [];

    // Add main answer
    contextParts.push(`${response.answer}\n`);

    // Add source references
    if (response.sources.length > 0) {
      contextParts.push("\nSources:");
      response.sources.forEach((source, index) => {
        const kbLabel = source.kb_name ? ` [${source.kb_name}]` : "";
        contextParts.push(
          `[${index + 1}]${kbLabel} ${source.title} - ${source.url}`
        );
      });
    }

    return contextParts.join("\n");
  }

  /**
   * Deduplicate sources by URL
   */
  private deduplicateSources(sources: KBSource[]): KBSource[] {
    const seen = new Set<string>();
    const deduplicated: KBSource[] = [];

    for (const source of sources) {
      if (!seen.has(source.url)) {
        seen.add(source.url);
        deduplicated.push(source);
      }
    }

    return deduplicated;
  }

  /**
   * Get KB health status
   */
  async getKBHealth(): Promise<{ knowledge_bases: KBHealthResponse[] }> {
    return kbService.checkKBHealth();
  }

  /**
   * List available knowledge bases
   */
  async listKnowledgeBases(): Promise<KBListResponse> {
    return kbService.listKnowledgeBases();
  }
}

// Singleton instance
let _ragService: RAGService | null = null;

export const ragService = {
  queryForChat: (
    ...args: Parameters<RAGService["queryForChat"]>
  ): ReturnType<RAGService["queryForChat"]> => {
    if (!_ragService) _ragService = new RAGService();
    return _ragService.queryForChat(...args);
  },
  queryForAnalysis: (
    ...args: Parameters<RAGService["queryForAnalysis"]>
  ): ReturnType<RAGService["queryForAnalysis"]> => {
    if (!_ragService) _ragService = new RAGService();
    return _ragService.queryForAnalysis(...args);
  },
  queryForProposal: (
    ...args: Parameters<RAGService["queryForProposal"]>
  ): ReturnType<RAGService["queryForProposal"]> => {
    if (!_ragService) _ragService = new RAGService();
    return _ragService.queryForProposal(...args);
  },
  queryMultipleTopics: (
    ...args: Parameters<RAGService["queryMultipleTopics"]>
  ): ReturnType<RAGService["queryMultipleTopics"]> => {
    if (!_ragService) _ragService = new RAGService();
    return _ragService.queryMultipleTopics(...args);
  },
  getKBHealth: (): ReturnType<RAGService["getKBHealth"]> => {
    if (!_ragService) _ragService = new RAGService();
    return _ragService.getKBHealth();
  },
  listKnowledgeBases: (): ReturnType<RAGService["listKnowledgeBases"]> => {
    if (!_ragService) _ragService = new RAGService();
    return _ragService.listKnowledgeBases();
  },
};
