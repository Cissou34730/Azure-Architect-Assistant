/**
 * OpenAI Client - Core LLM API wrapper
 * Handles authentication and API calls to OpenAI/Azure OpenAI
 */

import { logger as rootLogger } from "../logger.js";
import { OpenAIConfig } from "./types.js";

export class OpenAIClient {
  private config: OpenAIConfig;
  private log = rootLogger.child("OpenAIClient");

  constructor() {
    this.config = {
      apiKey:
        process.env.OPENAI_API_KEY || process.env.AZURE_OPENAI_API_KEY || "",
      apiEndpoint:
        process.env.OPENAI_API_ENDPOINT ||
        "https://api.openai.com/v1/chat/completions",
      model: process.env.OPENAI_MODEL || "gpt-4o-mini",
    };

    this.log.info("OpenAIClient initialized", {
      apiKeyPresent: Boolean(this.config.apiKey),
      model: this.config.model,
      endpoint: this.config.apiEndpoint,
    });
  }

  /**
   * Call OpenAI/Azure OpenAI API with system and user prompts
   */
  async complete(systemPrompt: string, userPrompt: string): Promise<string> {
    if (!this.config.apiKey) {
      this.log.error("OpenAI API key is missing");
      throw new Error(
        "OpenAI API key not configured. Set OPENAI_API_KEY or AZURE_OPENAI_API_KEY environment variable."
      );
    }

    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };

    // Determine if using Azure or OpenAI
    if (this.config.apiEndpoint.includes("azure.com")) {
      headers["api-key"] = this.config.apiKey;
    } else {
      headers["Authorization"] = `Bearer ${this.config.apiKey}`;
    }

    const body = {
      model: this.config.model,
      messages: [
        { role: "system", content: systemPrompt },
        { role: "user", content: userPrompt },
      ],
      temperature: 0.7,
      max_tokens: 4000,
    };

    this.log.info("Calling OpenAI API", {
      endpoint: this.config.apiEndpoint,
      model: this.config.model,
      payloadChars: systemPrompt.length + userPrompt.length,
    });

    try {
      const response = await fetch(this.config.apiEndpoint, {
        method: "POST",
        headers,
        body: JSON.stringify(body),
      });

      this.log.info("OpenAI API responded", { status: response.status });

      if (!response.ok) {
        const errorText = await response.text();
        this.log.error("OpenAI API error", {
          status: response.status,
          details: errorText.slice(0, 1000),
        });
        throw new Error(`OpenAI API error: ${response.status} - ${errorText}`);
      }

      const data = (await response.json()) as {
        choices: Array<{ message: { content: string } }>;
      };
      return data.choices[0].message.content;
    } catch (error) {
      this.log.error("OpenAI API call failed", error);
      throw error;
    }
  }

  /**
   * Get current model name
   */
  getModel(): string {
    return this.config.model;
  }
}

// Singleton instance
let _client: OpenAIClient | null = null;

export const openaiClient = {
  complete: (
    ...args: Parameters<OpenAIClient["complete"]>
  ): ReturnType<OpenAIClient["complete"]> => {
    if (!_client) _client = new OpenAIClient();
    return _client.complete(...args);
  },
  getModel: (): string => {
    if (!_client) _client = new OpenAIClient();
    return _client.getModel();
  },
};
