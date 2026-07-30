"use client";

import { useActionState, useEffect, useRef, type ReactNode } from "react";
import type { ActionResult } from "@/lib/action-result";
import { useSnackbar } from "@/components/organisms/SnackbarProvider";

type ServerFormAction = (
  prev: ActionResult | null,
  formData: FormData,
) => Promise<ActionResult>;

export function ActionForm({
  action,
  successMessage = "Saved.",
  resetOnSuccess = false,
  className = "",
  children,
}: {
  action: ServerFormAction;
  successMessage?: string;
  resetOnSuccess?: boolean;
  className?: string;
  children: ReactNode;
}) {
  const { success, error } = useSnackbar();
  const formRef = useRef<HTMLFormElement>(null);
  const lastSeen = useRef<ActionResult | null>(null);
  const [state, formAction] = useActionState(action, null);

  useEffect(() => {
    if (!state || state === lastSeen.current) return;
    lastSeen.current = state;
    if (state.ok) {
      success(state.message ?? successMessage);
      if (resetOnSuccess) formRef.current?.reset();
    } else {
      error(state.error);
    }
  }, [state, success, error, successMessage, resetOnSuccess]);

  return (
    <form ref={formRef} action={formAction} className={className}>
      {children}
    </form>
  );
}
