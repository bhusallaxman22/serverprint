import { type SelectHTMLAttributes } from "react";

type Props = SelectHTMLAttributes<HTMLSelectElement> & {
  label?: string;
  options: { value: string; label: string }[];
};

export function Select({ label, options, id, className = "", ...props }: Props) {
  const selectId = id ?? props.name;
  return (
    <label className="flex w-full flex-col gap-1.5 text-sm">
      {label ? <span className="text-text-muted">{label}</span> : null}
      <select
        id={selectId}
        className={`rounded-md border border-border bg-bg px-3 py-2 text-text outline-none ring-accent/40 focus:ring-2 ${className}`}
        {...props}
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </label>
  );
}
