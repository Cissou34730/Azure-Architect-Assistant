/**
 * Service Error Handler
 * Standardized error handling for API services
 */

export class ServiceError extends Error {
  constructor(
    message: string,
    public readonly status?: number,
    public readonly detail?: string,
  ) {
    super(message);
    this.name = "ServiceError";
  }
}

/**
 * Handle fetch response errors consistently
 */
export async function handleResponseError(
  response: Response,
  operation: string,
): Promise<never> {
  let errorMessage = `Failed to ${operation}`;
  let detail: string | undefined;

  try {
    const errorData = await response.json();
    if (errorData.error) {
      errorMessage = errorData.error;
    } else if (errorData.detail) {
      detail = errorData.detail;
    } else if (errorData.message) {
      errorMessage = errorData.message;
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
  options: RequestInit,
  operation: string,
): Promise<T> {
  try {
    const response = await fetch(url, options);

    if (!response.ok) {
      await handleResponseError(response, operation);
    }

    return await response.json();
  } catch (error) {
    if (error instanceof ServiceError) {
      throw error;
    }
    // Network error or other fetch failure
    throw new ServiceError(
      `Network error during ${operation}: ${
        error instanceof Error ? error.message : "Unknown error"
      }`,
      undefined,
      error instanceof Error ? error.message : undefined,
    );
  }
}
