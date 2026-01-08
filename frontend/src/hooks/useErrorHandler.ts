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

export function useErrorHandler() {
  const toast = useToast();

  const handleError = useCallback(
    (error: unknown, options: ErrorHandlerOptions = {}) => {
      const {
        message: customMessage,
        logToConsole = true,
        duration = 5000,
        showToast = true,
      } = options;

      // Extract error message
      let errorMessage = "An unexpected error occurred";

      if (error instanceof Error) {
        errorMessage = error.message;
      } else if (typeof error === "string") {
        errorMessage = error;
      } else if (error && typeof error === "object" && "message" in error) {
        errorMessage = String(error.message);
      }

      // Log to console if enabled
      if (logToConsole) {
        console.error("Error:", error);
      }

      // Show toast notification
      if (showToast) {
        toast.error(customMessage || errorMessage, duration);
      }

      return errorMessage;
    },
    [toast],
  );

  return {
    handleError,
    toast,
  };
}
