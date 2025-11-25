/**
 * LLM Service - Thin orchestration layer
 * Delegates to specialized services: ChatService, ProposalService
 * Maintains document analysis for initial project creation
 */

import { ProjectState, ConversationMessage } from "../models/Project.js";
import { logger as rootLogger } from "../logger.js";
import { openaiClient } from "./OpenAIClient.js";
import { chatService } from "./ChatService.js";
import { proposalService } from "./ProposalService.js";
import { LLMResponse, ProgressCallback } from "./types.js";

class LLMService {
  private log = rootLogger.child("LLMService");

  constructor() {
    this.log.info("LLMService initialized (orchestration layer)");
  }

  /**
   * Mode A: Document Analysis
   * Analyzes extracted text from documents and returns initial ProjectState
   */
  async analyzeDocuments(documentTexts: string[]): Promise<ProjectState> {
    this.log.info("Analyzing documents", {
      documentCount: documentTexts.length,
    });
    const combinedText = documentTexts.join("\n\n---\n\n");

    const systemPrompt = `You are an Azure Architecture Assistant. Analyze the provided project documents and extract key information to create a structured Architecture Sheet (ProjectState).

Your response MUST be a valid JSON object with the following structure:
{
  "context": {
    "summary": "Brief project summary",
    "objectives": ["objective1", "objective2"],
    "targetUsers": "Description of target users",
    "scenarioType": "Type of scenario (e.g., web app, IoT, data analytics)"
  },
  "nfrs": {
    "availability": "Availability requirements",
    "security": "Security requirements",
    "performance": "Performance requirements",
    "costConstraints": "Cost constraints"
  },
  "applicationStructure": {
    "components": [{"name": "component name", "description": "component description"}],
    "integrations": ["integration1", "integration2"]
  },
  "dataCompliance": {
    "dataTypes": ["data type1", "data type2"],
    "complianceRequirements": ["requirement1", "requirement2"],
    "dataResidency": "Data residency requirements"
  },
  "technicalConstraints": {
    "constraints": ["constraint1", "constraint2"],
    "assumptions": ["assumption1", "assumption2"]
  },
  "openQuestions": ["question1", "question2"]
}

Extract as much information as possible from the documents. For missing information, leave fields empty or use empty arrays.`;

    const userPrompt = `Analyze these project documents and extract the Architecture Sheet:\n\n${combinedText}`;

    const response = await openaiClient.complete(systemPrompt, userPrompt);
    this.log.info("Document analysis completed");

    const projectState = this.parseProjectStateFromResponse(
      response,
      `project-${Date.now()}`
    );
    return projectState;
  }

  /**
   * Mode B: Chat Clarification
   * Delegates to ChatService for interactive refinement
   */
  async processChatMessage(
    userMessage: string,
    currentState: ProjectState,
    recentMessages: ConversationMessage[]
  ): Promise<LLMResponse> {
    this.log.info("Delegating to ChatService", {
      projectId: currentState.projectId,
    });
    return chatService.processChatMessage(
      userMessage,
      currentState,
      recentMessages
    );
  }

  /**
   * Mode C: Architecture Proposal
   * Delegates to ProposalService for comprehensive proposal generation
   */
  async generateArchitectureProposal(
    state: ProjectState,
    onProgress?: ProgressCallback
  ): Promise<string> {
    this.log.info("Delegating to ProposalService", {
      projectId: state.projectId,
    });
    return proposalService.generateProposal(state, onProgress);
  }

  /**
   * Parse ProjectState from LLM response
   */
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  private parseProjectStateFromResponse(
    response: string,
    projectId: string
  ): ProjectState {
    const jsonMatch = response.match(/\{[\s\S]*\}/);
    if (!jsonMatch) {
      this.log.error("Failed to extract JSON from LLM response");
      throw new Error("Failed to extract JSON from LLM response");
    }

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const parsed = JSON.parse(jsonMatch[0]) as Record<string, any>;

    return {
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
  }
}

// Lazy initialization - only create instance when first accessed
let _llmService: LLMService | null = null;

export const llmService = {
  analyzeDocuments: (
    ...args: Parameters<LLMService["analyzeDocuments"]>
  ): ReturnType<LLMService["analyzeDocuments"]> => {
    if (!_llmService) _llmService = new LLMService();
    return _llmService.analyzeDocuments(...args);
  },
  processChatMessage: (
    ...args: Parameters<LLMService["processChatMessage"]>
  ): ReturnType<LLMService["processChatMessage"]> => {
    if (!_llmService) _llmService = new LLMService();
    return _llmService.processChatMessage(...args);
  },
  generateArchitectureProposal: (
    ...args: Parameters<LLMService["generateArchitectureProposal"]>
  ): ReturnType<LLMService["generateArchitectureProposal"]> => {
    if (!_llmService) _llmService = new LLMService();
    return _llmService.generateArchitectureProposal(...args);
  },
};
