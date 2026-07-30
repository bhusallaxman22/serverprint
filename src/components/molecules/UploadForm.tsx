"use client";

import { Input } from "@/components/atoms/Input";
import { SubmitButton } from "@/components/molecules/SubmitButton";
import { ActionForm } from "@/components/molecules/ActionForm";
import { uploadJobAction } from "@/app/actions";

export function UploadForm({ csrfToken }: { csrfToken: string }) {
  return (
    <ActionForm
      action={uploadJobAction}
      successMessage="Print job submitted."
      resetOnSuccess
      className="space-y-4"
    >
      <input type="hidden" name="csrfToken" value={csrfToken} />
      <label className="flex w-full flex-col gap-1.5 text-sm">
        <span className="text-text-muted">Document (PDF / PNG / JPG)</span>
        <input
          type="file"
          name="file"
          accept=".pdf,.png,.jpg,.jpeg,application/pdf,image/png,image/jpeg"
          required
          className="rounded-md border border-dashed border-border bg-bg px-3 py-6 text-sm file:mr-3 file:rounded file:border-0 file:bg-accent/15 file:px-3 file:py-1.5 file:text-accent"
        />
      </label>
      <Input label="Copies" name="copies" type="number" min={1} max={100} defaultValue={1} />
      <SubmitButton className="w-full sm:w-auto">Submit print job</SubmitButton>
    </ActionForm>
  );
}
