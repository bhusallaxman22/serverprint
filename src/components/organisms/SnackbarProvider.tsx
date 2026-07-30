"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { createPortal } from "react-dom";
import { Snackbar, type SnackbarItem, type SnackbarTone } from "@/components/atoms/Snackbar";

type ShowSnackbarInput = {
  message: string;
  tone?: SnackbarTone;
  durationMs?: number;
};

type SnackbarContextValue = {
  showSnackbar: (input: ShowSnackbarInput) => void;
  success: (message: string) => void;
  error: (message: string) => void;
  info: (message: string) => void;
};

const SnackbarContext = createContext<SnackbarContextValue | null>(null);

const DEFAULT_DURATION_MS = 4500;

export function SnackbarProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<SnackbarItem[]>([]);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const dismiss = useCallback((id: string) => {
    setItems((prev) => prev.filter((item) => item.id !== id));
  }, []);

  const showSnackbar = useCallback(
    ({ message, tone = "info", durationMs = DEFAULT_DURATION_MS }: ShowSnackbarInput) => {
      const id =
        typeof crypto !== "undefined" && "randomUUID" in crypto
          ? crypto.randomUUID()
          : `${Date.now()}-${Math.random()}`;
      setItems((prev) => [...prev.slice(-4), { id, message, tone }]);
      window.setTimeout(() => dismiss(id), durationMs);
    },
    [dismiss],
  );

  const value = useMemo<SnackbarContextValue>(
    () => ({
      showSnackbar,
      success: (message) => showSnackbar({ message, tone: "success" }),
      error: (message) => showSnackbar({ message, tone: "error" }),
      info: (message) => showSnackbar({ message, tone: "info" }),
    }),
    [showSnackbar],
  );

  return (
    <SnackbarContext.Provider value={value}>
      {children}
      {mounted
        ? createPortal(
            <div
              className="pointer-events-none fixed inset-x-0 bottom-0 z-[100] flex flex-col items-center gap-2 p-4 sm:items-end"
              aria-live="polite"
              aria-relevant="additions text"
              aria-atomic="false"
            >
              {items.map((item) => (
                <Snackbar key={item.id} item={item} onDismiss={dismiss} />
              ))}
            </div>,
            document.body,
          )
        : null}
    </SnackbarContext.Provider>
  );
}

export function useSnackbar(): SnackbarContextValue {
  const ctx = useContext(SnackbarContext);
  if (!ctx) {
    throw new Error("useSnackbar must be used within SnackbarProvider.");
  }
  return ctx;
}
