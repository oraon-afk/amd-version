"use client";

import { AnimatePresence, motion } from "framer-motion";
import { CheckCircle2, XCircle } from "lucide-react";
import { createContext, ReactNode, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";

type Toast = {
  id: string;
  title: string;
  description?: string;
  variant?: "success" | "error";
};

type ToastContextValue = {
  toast: (toast: Omit<Toast, "id">) => void;
};

const ToastContext = createContext<ToastContextValue | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const timeoutIds = useRef<Set<number>>(new Set());

  useEffect(() => {
    return () => {
      timeoutIds.current.forEach((timeoutId) => window.clearTimeout(timeoutId));
      timeoutIds.current.clear();
    };
  }, []);

  const toast = useCallback((next: Omit<Toast, "id">) => {
    const id = crypto.randomUUID();
    setToasts((items) => [...items, { ...next, id }]);
    const timeoutId = window.setTimeout(() => {
      timeoutIds.current.delete(timeoutId);
      setToasts((items) => items.filter((item) => item.id !== id));
    }, 4200);
    timeoutIds.current.add(timeoutId);
  }, []);

  const value = useMemo(() => ({ toast }), [toast]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="fixed right-4 top-4 z-50 flex w-[min(380px,calc(100vw-2rem))] flex-col gap-3">
        <AnimatePresence>
          {toasts.map((item) => {
            const Icon = item.variant === "error" ? XCircle : CheckCircle2;
            return (
              <motion.div
                key={item.id}
                initial={{ opacity: 0, y: -12, scale: 0.96 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: -12, scale: 0.96 }}
                className={`glass-panel rounded-xl p-4 border-l-2 ${item.variant === "error" ? "border-l-riskHigh" : "border-l-violet"}`}
              >
                <div className="flex gap-3">
                  <Icon className={item.variant === "error" ? "h-5 w-5 text-riskHigh" : "h-5 w-5 text-riskLow"} />
                  <div>
                    <div className="text-sm font-semibold">{item.title}</div>
                    {item.description && <p className="mt-1 text-sm text-muted">{item.description}</p>}
                  </div>
                </div>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) throw new Error("useToast must be used within ToastProvider");
  return context;
}
