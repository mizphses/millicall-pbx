import type { FormEvent, ReactNode } from "react";
import { css } from "../../styled-system/css";

interface FormCardProps {
  onSubmit: (e: FormEvent) => void;
  children: ReactNode;
  submitLabel?: string;
  cancelHref?: string;
  isSubmitting?: boolean;
}

export function FormCard({
  onSubmit,
  children,
  submitLabel = "保存",
  cancelHref,
  isSubmitting = false,
}: FormCardProps) {
  return (
    <div
      className={css({
        background: "#ffffff",
        border: "1px solid",
        borderColor: "#d4d2cd",
        borderRadius: "5px",
        padding: "20px",
      })}
    >
      <form onSubmit={onSubmit}>
        {children}
        <div
          className={css({
            display: "flex",
            flexDirection: "column",
            gap: "8px",
            marginTop: "24px",
            paddingTop: "16px",
            borderTop: "1px solid",
            borderColor: "#e6e4e0",
            sm: { flexDirection: "row" },
          })}
        >
          <button
            type="submit"
            disabled={isSubmitting}
            className={css({
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              gap: "4px",
              paddingInline: "18px",
              paddingBlock: "10px",
              fontSize: "14px",
              fontWeight: 500,
              borderRadius: "5px",
              background: "#c45d2c",
              color: "#ffffff",
              minHeight: "38px",
              cursor: "pointer",
              _hover: { background: "#a84e24" },
              _disabled: { opacity: "0.5" },
            })}
          >
            {isSubmitting ? "処理中..." : submitLabel}
          </button>
          {cancelHref && (
            <a
              href={cancelHref}
              className={css({
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                gap: "4px",
                paddingInline: "18px",
                paddingBlock: "10px",
                fontSize: "14px",
                fontWeight: 500,
                borderRadius: "5px",
                background: "#ffffff",
                color: "#1b1b1f",
                border: "1px solid",
                borderColor: "#d4d2cd",
                minHeight: "38px",
                _hover: { background: "#e6e4e0" },
              })}
            >
              キャンセル
            </a>
          )}
        </div>
      </form>
    </div>
  );
}

export function FormGroup({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: ReactNode;
}) {
  return (
    <div className={css({ marginBottom: "16px" })}>
      <label className={css({ display: "block", fontSize: "13px", fontWeight: 500, marginBottom: "4px" })}>
        {label}
      </label>
      {children}
      {hint && <div className={css({ fontSize: "12px", color: "#8e8e96", marginTop: "4px" })}>{hint}</div>}
    </div>
  );
}

export function FormRow({ children }: { children: ReactNode }) {
  return (
    <div
      className={css({
        display: "grid",
        gridTemplateColumns: "1fr",
        gap: "16px",
        sm: { gridTemplateColumns: "repeat(2, 1fr)" },
      })}
    >
      {children}
    </div>
  );
}

export function FormSection({ title }: { title: string }) {
  return (
    <div
      className={css({
        fontSize: "13px",
        fontWeight: 600,
        color: "#4a4a52",
        marginTop: "28px",
        marginBottom: "12px",
        paddingBottom: "6px",
        borderBottom: "2px solid",
        borderColor: "#e6e4e0",
        _first: { marginTop: "0" },
      })}
    >
      {title}
    </div>
  );
}

export const inputClass = css({
  width: "100%",
  paddingInline: "10px",
  paddingBlock: "8px",
  fontSize: "14px",
  color: "#1b1b1f",
  background: "#ffffff",
  border: "1px solid",
  borderColor: "#d4d2cd",
  borderRadius: "5px",
  outline: "none",
  minHeight: "38px",
  transition: "color 0.15s, background 0.15s",
  _focus: { borderColor: "#c45d2c", ringWidth: "2", ringColor: "rgba(196, 93, 44, 0.12)" },
});

export const selectClass = inputClass;

export const textareaClass = css({
  width: "100%",
  paddingInline: "10px",
  paddingBlock: "8px",
  fontSize: "14px",
  color: "#1b1b1f",
  background: "#ffffff",
  border: "1px solid",
  borderColor: "#d4d2cd",
  borderRadius: "5px",
  outline: "none",
  minHeight: "120px",
  resize: "vertical",
  transition: "color 0.15s, background 0.15s",
  _focus: { borderColor: "#c45d2c", ringWidth: "2", ringColor: "rgba(196, 93, 44, 0.12)" },
});
