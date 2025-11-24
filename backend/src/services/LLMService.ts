import { ProjectState, ConversationMessage } from "../models/Project.js";
import { logger as rootLogger } from "../logger.js";
import { wafService, WAFQueryResponse } from "./WAFService.js";

interface WAFSource {
  url: string;
  title: string;
  section: string;
  score: number;
}

interface LLMResponse {
  assistantMessage?: string;
  projectState: ProjectState;
  wafSources?: WAFSource[];
}

class LLMService {
  private apiKey: string;
  private apiEndpoint: string;
  private model: string;
  private log = rootLogger.child("LLMService");

  constructor() {
    this.apiKey =
      process.env.OPENAI_API_KEY || process.env.AZURE_OPENAI_API_KEY || "";
    this.apiEndpoint =
      process.env.OPENAI_API_ENDPOINT ||
      "https://api.openai.com/v1/chat/completions";
    this.model = process.env.OPENAI_MODEL || "gpt-4o-mini";

    this.log.info("LLMService initialized", {
      apiKeyPresent: Boolean(this.apiKey),
      model: this.model,
      endpoint: this.apiEndpoint,
    });
  }

  /**
   * Query WAF for Azure best practices and guidance
   */
  private async queryWAF(question: string): Promise<WAFQueryResponse | null> {
    try {
      this.log.info("Querying WAF", { question });
      const response = await wafService.query({ question, topK: 3 });

      if (!response.hasResults) {
        this.log.info("No WAF results found for question");
        return null;
      }

      this.log.info("WAF query successful", {
        sourceCount: response.sources.length,
        hasAnswer: Boolean(response.answer),
      });
      return response;
    } catch (error) {
      this.log.warn("WAF query failed, continuing without WAF context", {
        error,
      });
      return null;
    }
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
    "costConstraints": "Budget/cost constraints"
  },
  "applicationStructure": {
    "components": ["component1", "component2"],
    "integrations": ["integration1", "integration2"]
  },
  "dataCompliance": {
    "dataTypes": ["type1", "type2"],
    "complianceRequirements": ["requirement1", "requirement2"],
    "dataResidency": "Data residency requirements"
  },
  "technicalConstraints": {
    "constraints": ["constraint1", "constraint2"],
    "assumptions": ["assumption1", "assumption2"]
  },
  "openQuestions": ["question1", "question2"]
}

If information is not available in the documents, use "Not specified" or empty arrays as appropriate. Be thorough but concise.`;

    const userPrompt = `Analyze the following project documents and create a structured Architecture Sheet:\n\n${combinedText}`;

    const response = await this.callLLM(systemPrompt, userPrompt);
    this.log.info("Document analysis completed");

    return this.parseProjectStateFromResponse(response, "temp-project-id");
  }

  /**
   * Mode B: Chat Clarification
   * Processes user message with current state and returns updated state + assistant message
   */
  async processChatMessage(
    userMessage: string,
    currentState: ProjectState,
    recentMessages: ConversationMessage[]
  ): Promise<LLMResponse> {
    this.log.info("Processing chat message", {
      projectId: currentState.projectId,
      messageLength: userMessage.length,
      historyCount: recentMessages.length,
    });

    // Check if question is about Azure services, architecture, or best practices
    const azureKeywords = [
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
      "pillar",
      "reliability",
      "scalability",
      "monitoring",
      "deployment",
    ];
    const lowerMessage = userMessage.toLowerCase();
    const isAzureRelated = azureKeywords.some((keyword) =>
      lowerMessage.includes(keyword)
    );

    // Query WAF if Azure-related
    let wafContext = "";
    let wafSources: WAFSource[] | undefined;

    if (isAzureRelated) {
      this.log.info("Azure-related question detected, querying WAF");
      const wafResponse = await this.queryWAF(userMessage);

      if (wafResponse && wafResponse.hasResults) {
        wafContext = `\n\n=== Azure Well-Architected Framework Context ===\n${
          wafResponse.answer
        }\n\nSources:\n${wafResponse.sources
          .map((s, i) => `${i + 1}. ${s.title} (${s.section}) - ${s.url}`)
          .join(
            "\n"
          )}\n\nUse this WAF guidance to inform your response and cite sources when relevant.\n`;
        wafSources = wafResponse.sources;
        this.log.info("WAF context added to chat", {
          sourceCount: wafSources.length,
        });
      }
    }

    const conversationHistory = recentMessages
      .map(
        (msg) => `${msg.role === "user" ? "User" : "Assistant"}: ${msg.content}`
      )
      .join("\n");

    const systemPrompt = `You are an Azure Architecture Assistant helping to refine and clarify project requirements. 

Current Architecture Sheet:
${JSON.stringify(currentState, null, 2)}

You must:
1. Answer the user's question or address their input
2. Update the Architecture Sheet if new information is provided
3. Refine open questions, constraints, or NFRs as appropriate
4. When Azure Well-Architected Framework context is provided, incorporate it into your answer and cite sources${wafContext}

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

    const userPrompt = `Previous conversation:\n${conversationHistory}\n\nUser message: ${userMessage}`;

    const response = await this.callLLM(systemPrompt, userPrompt);
    this.log.info("Chat message processed");

    const result = this.parseChaClarificationResponse(
      response,
      currentState.projectId
    );

    // Add WAF sources if available
    if (wafSources && wafSources.length > 0) {
      result.wafSources = wafSources;
    }

    return result;
  }

  /**
   * Mode C: Architecture Proposal
   * Generates Azure high-level architecture based on ProjectState
   */
  async generateArchitectureProposal(
    state: ProjectState,
    onProgress?: (stage: string, detail?: string) => void
  ): Promise<string> {
    this.log.info("Generating architecture proposal", {
      projectId: state.projectId,
    });

    onProgress?.(
      "querying_waf",
      "Preparing to query Azure Well-Architected Framework"
    );

    // Query WAF for each pillar to get best practices
    this.log.info("Querying WAF for architecture guidance");

    const wafQueries = [
      `What are the security best practices for ${
        state.context.scenarioType || "cloud applications"
      }?`,
      `What are the reliability and availability best practices for ${
        state.context.scenarioType || "cloud applications"
      }?`,
      `What are the cost optimization best practices for Azure services?`,
      `What are the performance efficiency best practices for Azure?`,
      `What are the operational excellence best practices for Azure?`,
    ];

    this.log.info("About to query WAF sequentially", {
      queryCount: wafQueries.length,
    });

    // Query pillars sequentially to avoid overwhelming the Python service
    const wafResponses: (WAFQueryResponse | null)[] = [];
    const pillarNames = [
      "Security",
      "Reliability",
      "Cost Optimization",
      "Performance",
      "Operational Excellence",
    ];

    for (let i = 0; i < wafQueries.length; i++) {
      const pillarName = pillarNames[i];
      onProgress?.(
        "querying_waf",
        `Querying ${pillarName} pillar (${i + 1}/${wafQueries.length})`
      );
      this.log.info(`Querying WAF pillar ${i + 1}/${wafQueries.length}`);
      try {
        const response = await this.queryWAF(wafQueries[i]);
        wafResponses.push(response);
        this.log.info(`WAF pillar ${i + 1} completed`);
      } catch (error) {
        this.log.warn(`WAF pillar ${i + 1} failed, continuing`, { error });
        wafResponses.push(null);
      }
    }

    this.log.info("WAF queries completed", {
      responseCount: wafResponses.length,
      successCount: wafResponses.filter((r) => r !== null).length,
    });

    onProgress?.(
      "building_context",
      "Building proposal context from WAF guidance"
    );

    // Build WAF context from responses
    let wafContext = "";
    const allSources: WAFSource[] = [];

    wafResponses.forEach((response, index) => {
      if (response && response.hasResults) {
        const pillarName = [
          "Security",
          "Reliability",
          "Cost Optimization",
          "Performance",
          "Operational Excellence",
        ][index];
        wafContext += `\n\n=== ${pillarName} Pillar Guidance ===\n${response.answer}\n`;
        allSources.push(...response.sources);
      }
    });

    if (wafContext) {
      wafContext += `\n\n=== Sources ===\n${allSources
        .map((s, i) => `[${i + 1}] ${s.title} - ${s.url}`)
        .join(
          "\n"
        )}\n\nIMPORTANT: Cite these sources in your proposal using [1], [2], etc. format.\n`;
      this.log.info("WAF context added to proposal", {
        sourceCount: allSources.length,
      });
    }

    const systemPrompt = `You are an expert Azure Solution Architect. Based on the provided Architecture Sheet, generate a comprehensive high-level Azure architecture proposal.

Include:
1. Recommended Azure services and their purposes
2. Architecture diagram description (textual)
3. Key design decisions and rationale
4. Security considerations (cite WAF sources)
5. Scalability and availability approach (cite WAF sources)
6. Cost optimization suggestions (cite WAF sources)
7. Implementation phases/roadmap

Be specific about Azure services (e.g., Azure App Service, Azure SQL Database, Azure Functions, etc.).

When Azure Well-Architected Framework guidance is provided below, incorporate it into your recommendations and cite sources using [1], [2], etc.${wafContext}`;

    const userPrompt = `Generate a high-level Azure architecture proposal based on this Architecture Sheet:\n\n${JSON.stringify(
      state,
      null,
      2
    )}`;

    onProgress?.(
      "generating_proposal",
      "Generating comprehensive architecture proposal with AI"
    );
    const proposal = await this.callLLM(systemPrompt, userPrompt);
    this.log.info("Architecture proposal generated");

    onProgress?.("finalizing", "Finalizing proposal");
    return proposal;
  }

  /**
   * Core LLM API call
   */
  private async callLLM(
    systemPrompt: string,
    userPrompt: string
  ): Promise<string> {
    if (!this.apiKey) {
      this.log.error("OpenAI API key is missing");
      throw new Error(
        "OpenAI API key not configured. Set OPENAI_API_KEY or AZURE_OPENAI_API_KEY environment variable."
      );
    }

    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };

    // Determine if using Azure or OpenAI
    if (this.apiEndpoint.includes("azure.com")) {
      headers["api-key"] = this.apiKey;
    } else {
      headers["Authorization"] = `Bearer ${this.apiKey}`;
    }

    const body = {
      model: this.model,
      messages: [
        { role: "system", content: systemPrompt },
        { role: "user", content: userPrompt },
      ],
      temperature: 0.7,
      max_tokens: 4000,
    };

    this.log.info("Calling LLM", {
      endpoint: this.apiEndpoint,
      model: this.model,
      payloadChars: systemPrompt.length + userPrompt.length,
    });

    try {
      const response = await fetch(this.apiEndpoint, {
        method: "POST",
        headers,
        body: JSON.stringify(body),
      });

      this.log.info("LLM responded", { status: response.status });

      if (!response.ok) {
        const errorText = await response.text();
        this.log.error("LLM API error", {
          status: response.status,
          details: errorText.slice(0, 1000),
        });
        throw new Error(`LLM API error: ${response.status} - ${errorText}`);
      }

      const data = (await response.json()) as {
        choices: Array<{ message: { content: string } }>;
      };
      return data.choices[0].message.content;
    } catch (error) {
      this.log.error("LLM call failed", error);
      throw error;
    }
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

  /**
   * Parse chat clarification response (message + updated state)
   */
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  private parseChaClarificationResponse(
    response: string,
    projectId: string
  ): LLMResponse {
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
