import { Link } from "@tanstack/react-router";
import { css } from "../../../styled-system/css";

interface EditorToolbarProps {
  workflowName: string;
  onSave: () => void;
  isSaving: boolean;
  onAiGenerate?: () => void;
  isGenerating?: boolean;
}

const btnStyle = css({
  display: "inline-flex",
  alignItems: "center",
  justifyContent: "center",
  paddingInline: "14px",
  paddingBlock: "6px",
  fontSize: "13px",
  fontWeight: 500,
  borderRadius: "5px",
  cursor: "pointer",
  border: "none",
  _disabled: { opacity: 0.5, cursor: "default" },
});

export function EditorToolbar({
  workflowName,
  onSave,
  isSaving,
  onAiGenerate,
  isGenerating,
}: EditorToolbarProps) {
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
        to="/extensions"
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
        <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
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

      <div className={css({ display: "flex", gap: "8px" })}>
        {onAiGenerate && (
          <button
            type="button"
            onClick={onAiGenerate}
            disabled={isGenerating}
            className={`${btnStyle} ${css({
              background: "#673AB7",
              color: "#ffffff",
              _hover: { background: "#5e35b1" },
            })}`}
          >
            {isGenerating ? "生成中..." : "✦ AI生成"}
          </button>
        )}
        <button
          type="button"
          onClick={onSave}
          disabled={isSaving}
          className={`${btnStyle} ${css({
            background: "#c45d2c",
            color: "#ffffff",
            _hover: { background: "#a84e24" },
          })}`}
        >
          {isSaving ? "保存中..." : "保存"}
        </button>
      </div>
    </div>
  );
}
