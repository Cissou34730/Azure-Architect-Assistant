/**
 * Proposal Service - Generates comprehensive architecture proposals
 * Generic KB support - dynamically queries relevant topics, not hardcoded to WAF pillars
 */

import { ProjectState } from "../models/Project.js";
import { logger as rootLogger } from "../logger.js";
import { ragService } from "./RAGService.js";
import { openaiClient } from "./OpenAIClient.js";
import { ProgressCallback, KBSource } from "./types.js";

export class ProposalService {
  private log = rootLogger.child("ProposalService");

  /**
   * Generate comprehensive architecture proposal based on ProjectState
   * Dynamically determines relevant topics to query based on scenario
   */
  async generateProposal(
    state: ProjectState,
    onProgress?: ProgressCallback
  ): Promise<string> {
    this.log.info("Generating architecture proposal", {
      projectId: state.projectId,
    });

    onProgress?.(
      "preparing_queries",
      "Determining relevant architecture topics"
    );

    // Dynamically build queries based on project context
    const queries = this.buildRelevantQueries(state);

    this.log.info("Built architecture queries", {
      queryCount: queries.length,
      topics: queries.map((q) => q.substring(0, 50)),
    });

    onProgress?.(
      "querying_knowledge_bases",
      `Querying ${queries.length} architecture topics`
    );

    // Query knowledge bases with proposal profile (comprehensive results)
    const ragResult = await ragService.queryForProposal(queries);

    this.log.info("KB queries completed", {
      hasResults: ragResult.hasResults,
      sourceCount: ragResult.sources.length,
    });

    onProgress?.(
      "building_context",
      "Building proposal context from knowledge base guidance"
    );

    // Format KB context for prompt
    const kbContext = this.formatKBContext(
      ragResult.context,
      ragResult.sources as KBSource[]
    );

    // Build system prompt
    const systemPrompt = this.buildProposalSystemPrompt(kbContext);

    // Build user prompt with project state
    const userPrompt = `Generate a high-level Azure architecture proposal based on this Architecture Sheet:\n\n${JSON.stringify(
      state,
      null,
      2
    )}`;

    onProgress?.(
      "generating_proposal",
      "Generating comprehensive architecture proposal with AI"
    );

    // Call OpenAI
    const proposal = await openaiClient.complete(systemPrompt, userPrompt);
    this.log.info("Architecture proposal generated", {
      proposalLength: proposal.length,
    });

    onProgress?.("finalizing", "Finalizing proposal");
    return proposal;
  }

  /**
   * Build relevant queries based on project context
   * NOT hardcoded to WAF pillars - adapts to scenario
   */
  private buildRelevantQueries(state: ProjectState): string[] {
    const scenarioType = state.context.scenarioType || "cloud applications";
    const queries: string[] = [];

    // Core architecture topics
    queries.push(
      `What are the security best practices for ${scenarioType}?`,
      `What are the reliability and availability best practices for ${scenarioType}?`,
      `What are the cost optimization best practices for Azure services?`,
      `What are the performance efficiency best practices for Azure?`,
      `What are the operational excellence best practices for Azure?`
    );

    // Add scenario-specific queries
    if (scenarioType.toLowerCase().includes("iot")) {
      queries.push(
        `What are IoT architecture best practices for Azure?`,
        `How to implement IoT security and device management?`
      );
    }

    if (scenarioType.toLowerCase().includes("data")) {
      queries.push(
        `What are data architecture best practices for Azure?`,
        `How to implement data governance and compliance?`
      );
    }

    if (
      scenarioType.toLowerCase().includes("api") ||
      scenarioType.toLowerCase().includes("microservice")
    ) {
      queries.push(
        `What are API and microservices best practices for Azure?`,
        `How to implement API gateway and service mesh patterns?`
      );
    }

    // Add queries based on specific NFRs
    if (
      state.nfrs.security &&
      state.nfrs.security.toLowerCase().includes("zero trust")
    ) {
      queries.push(
        `What are Zero Trust architecture best practices for Azure?`
      );
    }

    if (state.dataCompliance.complianceRequirements.length > 0) {
      queries.push(
        `What are compliance and data residency best practices for Azure?`
      );
    }

    return queries;
  }

  /**
   * Format KB context for inclusion in prompt
   */
  private formatKBContext(context: string, sources: KBSource[]): string {
    let kbContext = "";

    if (context && sources.length > 0) {
      kbContext = `\n\n=== Architecture Best Practices (from Knowledge Bases) ===\n${context}\n`;

      kbContext += `\n\n=== Sources ===\n${sources
        .map((s, i) => {
          const kbLabel = s.kb_name ? ` [${s.kb_name}]` : "";
          return `[${i + 1}]${kbLabel} ${s.title} - ${s.url}`;
        })
        .join(
          "\n"
        )}\n\nIMPORTANT: Cite these sources in your proposal using [1], [2], etc. format.\n`;

      this.log.info("KB context formatted", {
        contextLength: kbContext.length,
        sourceCount: sources.length,
      });
    }

    return kbContext;
  }

  /**
   * Build system prompt for proposal generation
   */
  private buildProposalSystemPrompt(kbContext: string): string {
    return `You are an expert Azure Solution Architect. Based on the provided Architecture Sheet, generate a comprehensive high-level Azure architecture proposal.

Include:
1. Recommended Azure services and their purposes
2. Architecture diagram description (textual)
3. Key design decisions and rationale
4. Security considerations (cite sources from knowledge bases)
5. Scalability and availability approach (cite sources)
6. Cost optimization suggestions (cite sources)
7. Operational excellence recommendations (cite sources)
8. Implementation phases/roadmap

Be specific about Azure services (e.g., Azure App Service, Azure SQL Database, Azure Functions, etc.).

When knowledge base guidance is provided below, incorporate it into your recommendations and cite sources using [1], [2], etc.${kbContext}`;
  }
}

// Singleton instance
let _proposalService: ProposalService | null = null;

export const proposalService = {
  generateProposal: (
    ...args: Parameters<ProposalService["generateProposal"]>
  ): ReturnType<ProposalService["generateProposal"]> => {
    if (!_proposalService) _proposalService = new ProposalService();
    return _proposalService.generateProposal(...args);
  },
};
