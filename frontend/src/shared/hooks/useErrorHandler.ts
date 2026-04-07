/**
 * useErrorHandler Hook
 * Standardized error handling with toast notifications
 */

import { useCallback } from "react";
import { useToast } from "./useToast";

export interface ErrorHandlerOptions {
  /**
   * Custom error message to display instead of the error's message
   */
  message?: string;

  /**
   * Whether to log the error to console
   * @default true
   */
  logToConsole?: boolean;

  /**
   * Toast duration in milliseconds
   * @default 5000
   */
  duration?: number;

  /**
   * Whether to show toast notification
   * @default true
   */
  showToast?: boolean;
}

/**
 * Extracts a readable error message from various error types
 */
// eslint-disable-next-line @typescript-eslint/no-restricted-types
function extractErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }
  if (typeof error === "string" && error !== "") {
    return error;
  }
  if (
    error !== null &&
    typeof error === "object" &&
    "message" in error &&
    typeof error.message === "string"
  ) {
    return error.message;
  }
  return "An unexpected error occurred";
}

export function useErrorHandler() {
  const toast = useToast();

  const handleError = useCallback(
    // eslint-disable-next-line @typescript-eslint/no-restricted-types
    (error: unknown, options: ErrorHandlerOptions = {}) => {
      const {
        message: customMessage,
        logToConsole = true,
        duration = 5000,
        showToast = true,
      } = options;

      const errorMessage = extractErrorMessage(error);

      if (logToConsole) {
        console.error("Error extracted:", errorMessage, error);
      }

      if (showToast) {
        toast.error(
          customMessage !== undefined && customMessage !== ""
            ? customMessage
            : errorMessage,
          duration
        );
      }

      return errorMessage;
    },
    [toast]
  );

  return {
    handleError,
    toast,
  };
}
