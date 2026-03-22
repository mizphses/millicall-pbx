import { Link } from "@tanstack/react-router";
import { css } from "../../../styled-system/css";

interface EditorToolbarProps {
  workflowName: string;
  onSave: () => void;
  isSaving: boolean;
}

export function EditorToolbar({ workflowName, onSave, isSaving }: EditorToolbarProps) {
  return (
    <div
      className={css({
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        height: "48px",
        padding: "0 16px",
        background: "#ffffff",
        borderBottom: "1px solid #d4d2cd",
        flexShrink: 0,
      })}
    >
      <Link
        to="/workflows"
        className={css({
          display: "inline-flex",
          alignItems: "center",
          gap: "6px",
          fontSize: "13px",
          fontWeight: 500,
          color: "#4a4a52",
          textDecoration: "none",
          _hover: { color: "#1b1b1f" },
        })}
      >
        <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
          <path d="M10.354 3.354a.5.5 0 00-.708-.708l-5 5a.5.5 0 000 .708l5 5a.5.5 0 00.708-.708L5.707 8l4.647-4.646z" />
        </svg>
        戻る
      </Link>

      <span
        className={css({
          fontSize: "15px",
          fontWeight: 700,
          color: "#1b1b1f",
          letterSpacing: "-0.02em",
        })}
      >
        {workflowName}
      </span>

      <button
        type="button"
        onClick={onSave}
        disabled={isSaving}
        className={css({
          display: "inline-flex",
          alignItems: "center",
          justifyContent: "center",
          paddingInline: "16px",
          paddingBlock: "6px",
          fontSize: "13px",
          fontWeight: 500,
          borderRadius: "5px",
          background: "#c45d2c",
          color: "#ffffff",
          cursor: "pointer",
          border: "none",
          _hover: { background: "#a84e24" },
          _disabled: { opacity: "0.5", cursor: "default" },
        })}
      >
        {isSaving ? "保存中..." : "保存"}
      </button>
    </div>
  );
}
