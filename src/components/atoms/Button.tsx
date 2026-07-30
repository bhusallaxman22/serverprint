import { type ButtonHTMLAttributes } from "react";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "danger" | "ghost";
  size?: "sm" | "md";
};

const variants: Record<NonNullable<Props["variant"]>, string> = {
  primary:
    "bg-accent text-bg hover:brightness-110 disabled:opacity-50",
  secondary:
    "bg-bg-panel border border-border text-text hover:border-accent/50 disabled:opacity-50",
  danger: "bg-danger/15 text-danger border border-danger/30 hover:bg-danger/25",
  ghost: "text-text-muted hover:text-text hover:bg-white/5",
};

export function Button({
  variant = "primary",
  size = "md",
  className = "",
  ...props
}: Props) {
  return (
    <button
      className={`inline-flex items-center justify-center rounded-md font-medium transition ${
        size === "sm" ? "px-2.5 py-1.5 text-xs" : "px-3.5 py-2 text-sm"
      } ${variants[variant]} ${className}`}
      {...props}
    />
  );
}
