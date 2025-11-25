/**
 * Chat Service - Handles interactive chat clarification
 * Generic KB support - works with any knowledge base, not just WAF
 */

import { ProjectState, ConversationMessage } from "../models/Project.js";
import { logger as rootLogger } from "../logger.js";
import { ragService } from "./RAGService.js";
import { openaiClient } from "./OpenAIClient.js";
import { LLMResponse, KBSource } from "./types.js";

export class ChatService {
  private log = rootLogger.child("ChatService");

  /**
   * Process a chat message in the context of an existing project
   * Queries knowledge bases for Azure-related questions
   * Updates ProjectState based on conversation
   */
  async processChatMessage(
    userMessage: string,
    currentState: ProjectState,
    recentMessages: ConversationMessage[]
  ): Promise<LLMResponse> {
    this.log.info("Processing chat message", {
      projectId: currentState.projectId,
      messageLength: userMessage.length,
    });

    // Detect if message is Azure/architecture-related
    const isArchitectureRelated = this.detectArchitectureKeywords(userMessage);

    // Query knowledge bases if architecture-related
    let kbContext = "";
    let kbSources: KBSource[] | undefined;

    if (isArchitectureRelated) {
      this.log.info(
        "Architecture-related question detected, querying knowledge bases"
      );
      const kbResponse = await this.queryKnowledgeBases(userMessage);

      if (kbResponse && kbResponse.hasResults) {
        kbContext = this.formatKBContext(kbResponse.sources);
        kbSources = kbResponse.sources;
        this.log.info("KB context added to chat", {
          sourceCount: kbSources.length,
        });
      }
    }

    // Build conversation history
    const conversationHistory = recentMessages
      .map(
        (msg) => `${msg.role === "user" ? "User" : "Assistant"}: ${msg.content}`
      )
      .join("\n");

    // Build prompt
    const systemPrompt = this.buildChatSystemPrompt(
      currentState,
      kbContext,
      Boolean(kbContext)
    );
    const userPrompt = `Previous conversation:\n${conversationHistory}\n\nUser message: ${userMessage}`;

    // Call OpenAI
    const response = await openaiClient.complete(systemPrompt, userPrompt);
    this.log.info("Chat message processed");

    // Parse response
    const result = this.parseChatResponse(response, currentState.projectId);

    // Add KB sources if available
    if (kbSources && kbSources.length > 0) {
      result.sources = kbSources;
    }

    return result;
  }

  /**
   * Detect if message contains architecture/cloud keywords
   */
  private detectArchitectureKeywords(message: string): boolean {
    const keywords = [
      "azure",
      "app service",
      "function",
      "cosmos",
      "sql",
      "storage",
      "kubernetes",
      "aks",
      "security",
      "availability",
      "performance",
      "cost",
      "architecture",
      "best practice",
      "recommendation",
      "reliability",
      "scalability",
      "monitoring",
      "deployment",
      "cloud",
      "service",
      "database",
      "api",
      "microservice",
    ];

    const lowerMessage = message.toLowerCase();
    return keywords.some((keyword) => lowerMessage.includes(keyword));
  }

  /**
   * Query knowledge bases for relevant information
   */
  private async queryKnowledgeBases(question: string): Promise<{
    answer: string;
    sources: KBSource[];
    hasResults: boolean;
  } | null> {
    try {
      this.log.info("Querying knowledge bases", {
        question: question.substring(0, 100),
      });
      const result = await ragService.queryForChat(question);

      if (!result.hasResults) {
        this.log.info("No KB results found for question");
        return null;
      }

      this.log.info("KB query successful", {
        sourceCount: result.sources.length,
        hasContext: Boolean(result.context),
      });

      // Extract answer from context (first paragraph)
      const answer = result.context.split("\n\n")[0] || result.context;

      return {
        answer,
        sources: result.sources as KBSource[],
        hasResults: result.hasResults,
      };
    } catch (error) {
      this.log.warn("KB query failed, continuing without KB context", {
        error,
      });
      return null;
    }
  }

  /**
   * Format KB sources for inclusion in prompt
   */
  private formatKBContext(sources: KBSource[]): string {
    const sourcesText = sources
      .map((s, i) => {
        const kbLabel = s.kb_name ? ` [${s.kb_name}]` : "";
        return `${i + 1}.${kbLabel} ${s.title} (${s.section}) - ${s.url}`;
      })
      .join("\n");

    return `\n\n=== Knowledge Base Context (Cloud Best Practices) ===\nSources:\n${sourcesText}\n\nUse this guidance to inform your response and cite sources when relevant.\n`;
  }

  /**
   * Build system prompt for chat
   */
  private buildChatSystemPrompt(
    currentState: ProjectState,
    kbContext: string,
    hasKBContext: boolean
  ): string {
    return `You are an Azure Architecture Assistant helping to refine and clarify project requirements. 

Current Architecture Sheet:
${JSON.stringify(currentState, null, 2)}

You must:
1. Answer the user's question or address their input
2. Update the Architecture Sheet if new information is provided
3. Refine open questions, constraints, or NFRs as appropriate
${
  hasKBContext
    ? "4. When knowledge base context is provided, incorporate it into your answer and cite sources"
    : ""
}${kbContext}

Your response MUST contain:
1. A conversational message to the user
2. An updated ProjectState JSON object

Format your response as:
MESSAGE: [Your conversational response]

PROJECT_STATE_JSON:
{
  "context": {...},
  "nfrs": {...},
  "applicationStructure": {...},
  "dataCompliance": {...},
  "technicalConstraints": {...},
  "openQuestions": [...]
}`;
  }

  /**
   * Parse chat clarification response (message + updated state)
   */
  private parseChatResponse(response: string, projectId: string): LLMResponse {
    const messageMatch = response.match(
      /MESSAGE:\s*([\s\S]*?)(?=PROJECT_STATE_JSON:|$)/
    );
    const jsonMatch = response.match(/PROJECT_STATE_JSON:\s*(\{[\s\S]*\})/);

    const assistantMessage = messageMatch ? messageMatch[1].trim() : response;
    let projectState: ProjectState;

    if (jsonMatch) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const parsed = JSON.parse(jsonMatch[1]) as Record<string, any>;
      projectState = {
        projectId,
        // eslint-disable-next-line @typescript-eslint/no-unsafe-assignment, @typescript-eslint/no-unsafe-member-access
        context: parsed.context,
        // eslint-disable-next-line @typescript-eslint/no-unsafe-assignment, @typescript-eslint/no-unsafe-member-access
        nfrs: parsed.nfrs,
        // eslint-disable-next-line @typescript-eslint/no-unsafe-assignment, @typescript-eslint/no-unsafe-member-access
        applicationStructure: parsed.applicationStructure,
        // eslint-disable-next-line @typescript-eslint/no-unsafe-assignment, @typescript-eslint/no-unsafe-member-access
        dataCompliance: parsed.dataCompliance,
        // eslint-disable-next-line @typescript-eslint/no-unsafe-assignment, @typescript-eslint/no-unsafe-member-access
        technicalConstraints: parsed.technicalConstraints,
        // eslint-disable-next-line @typescript-eslint/no-unsafe-assignment, @typescript-eslint/no-unsafe-member-access
        openQuestions: parsed.openQuestions || [],
        lastUpdated: new Date().toISOString(),
      };
    } else {
      // Fallback parsing
      const fallbackJsonMatch = response.match(/\{[\s\S]*\}/);
      if (fallbackJsonMatch) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any, @typescript-eslint/no-unsafe-assignment
        const parsed = JSON.parse(fallbackJsonMatch[0]);
        projectState = {
          projectId,
          // eslint-disable-next-line @typescript-eslint/no-unsafe-assignment, @typescript-eslint/no-unsafe-member-access
          context: parsed.context || {
            summary: "",
            objectives: [],
            targetUsers: "",
            scenarioType: "",
          },
          // eslint-disable-next-line @typescript-eslint/no-unsafe-assignment, @typescript-eslint/no-unsafe-member-access
          nfrs: parsed.nfrs || {
            availability: "",
            security: "",
            performance: "",
            costConstraints: "",
          },
          // eslint-disable-next-line @typescript-eslint/no-unsafe-assignment, @typescript-eslint/no-unsafe-member-access
          applicationStructure: parsed.applicationStructure || {
            components: [],
            integrations: [],
          },
          // eslint-disable-next-line @typescript-eslint/no-unsafe-assignment, @typescript-eslint/no-unsafe-member-access
          dataCompliance: parsed.dataCompliance || {
            dataTypes: [],
            complianceRequirements: [],
            dataResidency: "",
          },
          // eslint-disable-next-line @typescript-eslint/no-unsafe-assignment, @typescript-eslint/no-unsafe-member-access
          technicalConstraints: parsed.technicalConstraints || {
            constraints: [],
            assumptions: [],
          },
          // eslint-disable-next-line @typescript-eslint/no-unsafe-assignment, @typescript-eslint/no-unsafe-member-access
          openQuestions: parsed.openQuestions || [],
          lastUpdated: new Date().toISOString(),
        };
      } else {
        this.log.error(
          "Failed to extract ProjectState JSON from chat response"
        );
        throw new Error(
          "Failed to extract ProjectState JSON from chat response"
        );
      }
    }

    return { assistantMessage, projectState };
  }
}

// Singleton instance
let _chatService: ChatService | null = null;

export const chatService = {
  processChatMessage: (
    ...args: Parameters<ChatService["processChatMessage"]>
  ): ReturnType<ChatService["processChatMessage"]> => {
    if (!_chatService) _chatService = new ChatService();
    return _chatService.processChatMessage(...args);
  },
};
