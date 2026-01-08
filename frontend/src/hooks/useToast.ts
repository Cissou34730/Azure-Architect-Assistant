/**
 * useToast Hook
 * Manages toast notifications state and provides simple API
 */

import { useState, useCallback } from "react";
import type { Toast, ToastType } from "../components/common/Toast";

let toastIdCounter = 0;

export function useToast() {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const show = useCallback(
    (message: string, type: ToastType = "info", duration = 5000) => {
      const id = `toast-${++toastIdCounter}`;
      const toast: Toast = { id, message, type, duration };

      setToasts((prev) => [...prev, toast]);

      return id;
    },
    [],
  );

  const success = useCallback(
    (message: string, duration?: number) => {
      return show(message, "success", duration);
    },
    [show],
  );

  const error = useCallback(
    (message: string, duration?: number) => {
      return show(message, "error", duration);
    },
    [show],
  );

  const warning = useCallback(
    (message: string, duration?: number) => {
      return show(message, "warning", duration);
    },
    [show],
  );

  const info = useCallback(
    (message: string, duration?: number) => {
      return show(message, "info", duration);
    },
    [show],
  );

  const close = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const closeAll = useCallback(() => {
    setToasts([]);
  }, []);

  return {
    toasts,
    show,
    success,
    error,
    warning,
    info,
    close,
    closeAll,
  };
}
