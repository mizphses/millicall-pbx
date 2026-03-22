import { css } from "../../styled-system/css";

type TagVariant = "ok" | "ng" | "info" | "muted" | "phone" | "ai" | "ivr" | "workflow" | "accent";

const variants: Record<TagVariant, { bg: string; color: string }> = {
  ok: { bg: "#e3f4eb", color: "#2a7e4f" },
  ng: { bg: "#fce8e8", color: "#b83232" },
  info: { bg: "#e5ecf5", color: "#365a8a" },
  muted: { bg: "#e6e4e0", color: "#4a4a52" },
  phone: { bg: "#dbeafe", color: "#1e40af" },
  ai: { bg: "#ede9fe", color: "#6d28d9" },
  ivr: { bg: "#fef3c7", color: "#92400e" },
  workflow: { bg: "#fce7f3", color: "#9d174d" },
  accent: { bg: "#fdf3ee", color: "#c45d2c" },
};

interface TagProps {
  variant: TagVariant;
  children: React.ReactNode;
}

export function Tag({ variant, children }: TagProps) {
  const v = variants[variant];
  return (
    <span
      className={css({
        display: "inline-block",
        paddingInline: "8px",
        paddingBlock: "2px",
        borderRadius: "3px",
        fontSize: "11px",
        fontWeight: 600,
        letterSpacing: "-0.02em",
        background: v.bg,
        color: v.color,
      })}
    >
      {children}
    </span>
  );
}
