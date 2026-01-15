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
    []
  );

  const success = useCallback(
    (msg: string, d?: number) => {
      show(msg, "success", d);
    },
    [show]
  );
  const error = useCallback(
    (msg: string, d?: number) => {
      show(msg, "error", d);
    },
    [show]
  );
  const warning = useCallback(
    (msg: string, d?: number) => {
      show(msg, "warning", d);
    },
    [show]
  );
  const info = useCallback(
    (msg: string, d?: number) => {
      show(msg, "info", d);
    },
    [show]
  );

  const close = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const closeAll = useCallback(() => {
    setToasts([]);
  }, []);

  return { toasts, show, success, error, warning, info, close, closeAll };
}
