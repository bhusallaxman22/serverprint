import { type InputHTMLAttributes } from "react";

type Props = InputHTMLAttributes<HTMLInputElement> & {
  label?: string;
};

export function Input({ label, id, className = "", ...props }: Props) {
  const inputId = id ?? props.name;
  return (
    <label className="flex w-full flex-col gap-1.5 text-sm">
      {label ? <span className="text-text-muted">{label}</span> : null}
      <input
        id={inputId}
        className={`rounded-md border border-border bg-bg px-3 py-2 text-text outline-none ring-accent/40 placeholder:text-text-muted/60 focus:ring-2 ${className}`}
        {...props}
      />
    </label>
  );
}
