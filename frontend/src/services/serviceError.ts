/**
 * Service Error Handler
 * Standardized error handling for API services
 */

export class ServiceError extends Error {
  constructor(
    message: string,
    public readonly status?: number,
    public readonly detail?: string
  ) {
    super(message);
    this.name = "ServiceError";
  }
}

import { keysToCamel } from "../utils/apiMapping";
import { isRecord } from "../utils/typeGuards";

// ... (ServiceError class)

 
function getErrorMessageFromData(
  // eslint-disable-next-line @typescript-eslint/no-restricted-types
  rawData: Record<string, unknown>
): string | null {
  if (typeof rawData.error === "string" && rawData.error !== "") {
    return rawData.error;
  }

  if (typeof rawData.message === "string" && rawData.message !== "") {
    return rawData.message;
  }

  return null;
}

 
function getErrorDetailFromData(
  // eslint-disable-next-line @typescript-eslint/no-restricted-types
  rawData: Record<string, unknown>
): string | null {
  if (typeof rawData.detail === "string" && rawData.detail !== "") {
    return rawData.detail;
  }
  return null;
}

/**
 * Handle fetch response errors consistently
 */
export async function handleResponseError(
  response: Response,
  operation: string
): Promise<never> {
  let errorMessage = `Failed to ${operation}`;
  let detail: string | undefined;

  try {
    // eslint-disable-next-line @typescript-eslint/no-restricted-types
    const rawData: unknown = await response.json();
    if (isRecord(rawData)) {
      const extractedMsg = getErrorMessageFromData(rawData);
      if (extractedMsg !== null) {
        errorMessage = extractedMsg;
      }

      const extractedDetail = getErrorDetailFromData(rawData);
      if (extractedDetail !== null) {
        detail = extractedDetail;
      }
    }
  } catch {
    // Response wasn't JSON, use status text
    errorMessage = `${operation} failed: ${response.statusText}`;
  }

  throw new ServiceError(errorMessage, response.status, detail);
}

/**
 * Wrap fetch calls with consistent error handling
 */
export async function fetchWithErrorHandling<T>(
  url: string,
  options: RequestInit = {},
  operation = "fetch"
): Promise<T> {
  try {
    const response = await fetch(url, options);

    if (!response.ok) {
      await handleResponseError(response, operation);
    }

    const text = await response.text();
    if (text === "") {
      return keysToCamel<T>({});
    }
    // eslint-disable-next-line @typescript-eslint/no-restricted-types
    const data: unknown = JSON.parse(text);
    return keysToCamel<T>(data);
  } catch (error) {
    if (error instanceof ServiceError) {
      throw error;
    }
    // Network error or other fetch failure
    const errorMsg = error instanceof Error ? error.message : "Unknown error";
    throw new ServiceError(
      `Network error during ${operation}: ${errorMsg}`,
      undefined,
      errorMsg
    );
  }
}
