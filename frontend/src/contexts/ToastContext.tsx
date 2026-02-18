import { createContext, useContext, ReactNode } from "react";
import { useToast } from "../hooks/useToast";
import { ToastContainer } from "../components/common";
import type { Toast } from "../components/common/Toast";

interface ToastContextValue {
  readonly toasts: Toast[];
  readonly show: (message: string, type?: "success" | "error" | "warning" | "info", duration?: number) => string;
  readonly success: (msg: string, duration?: number) => void;
  readonly error: (msg: string, duration?: number) => void;
  readonly warning: (msg: string, duration?: number) => void;
  readonly info: (msg: string, duration?: number) => void;
  readonly close: (id: string) => void;
  readonly closeAll: () => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

interface ToastProviderProps {
  readonly children: ReactNode;
}

export function ToastProvider({ children }: ToastProviderProps) {
  const toast = useToast();

  return (
    <ToastContext.Provider value={toast}>
      {children}
      <ToastContainer toasts={toast.toasts} onClose={toast.close} />
    </ToastContext.Provider>
  );
}

export function useToastContext(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (ctx === null) {
    throw new Error("useToastContext must be used within a ToastProvider");
  }
  return ctx;
}
