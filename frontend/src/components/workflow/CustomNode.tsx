import { Handle, Position, type NodeProps } from "@xyflow/react";
import { css } from "../../../styled-system/css";

export interface CustomNodeData {
  label: string;
  nodeType: string;
  color: string;
  config: Record<string, unknown>;
  outputHandles?: { id: string; label: string }[];
  [key: string]: unknown;
}

/** Node types that have multiple labeled outputs */
const BRANCHING_OUTPUTS: Record<string, (config: Record<string, unknown>) => { id: string; label: string }[]> = {
  condition: () => [
    { id: "true", label: "True" },
    { id: "false", label: "False" },
  ],
  time_condition: () => [
    { id: "match", label: "営業時間内" },
    { id: "no_match", label: "営業時間外" },
  ],
  api_call: () => [
    { id: "success", label: "成功" },
    { id: "error", label: "エラー" },
  ],
  menu: (_config) => {
    // Generate handles for DTMF digits 0-9 + timeout
    const handles = [];
    for (let i = 1; i <= 9; i++) {
      handles.push({ id: String(i), label: String(i) });
    }
    handles.push({ id: "0", label: "0" });
    handles.push({ id: "timeout", label: "タイムアウト" });
    return handles;
  },
  dtmf_input: (_config) => {
    const maxDigits = Number(_config.max_digits || 1);
    if (maxDigits === 1) {
      const handles = [];
      for (let i = 1; i <= 9; i++) {
        handles.push({ id: String(i), label: String(i) });
      }
      handles.push({ id: "0", label: "0" });
      return handles;
    }
    // Multi-digit: single output (stored in variable, use condition node for routing)
    return [];
  },
  intent_detection: (config) => {
    const intents = config.intents;
    if (Array.isArray(intents)) {
      return intents
        .filter((i): i is { key: string; value: string } => typeof i === "object" && i !== null && "key" in i)
        .map((i) => ({ id: i.key, label: i.value || i.key }));
    }
    return [{ id: "other", label: "その他" }];
  },
};

export function CustomNode({ data, selected }: NodeProps) {
  const nodeData = data as unknown as CustomNodeData;
  const { label, color, config, nodeType } = nodeData;

  const branchFn = BRANCHING_OUTPUTS[nodeType];
  const outputHandles = branchFn ? branchFn(config || {}) : [];
  const hasBranching = outputHandles.length > 0;
  const isTerminal = nodeType === "end" || nodeType === "hangup" || nodeType === "voicemail" || nodeType === "human_escalation";
  const isStart = nodeType === "start";

  const configPreview = Object.entries(config || {})
    .filter(([k, v]) => v !== "" && v !== undefined && v !== null && k !== "intents" && k !== "fields")
    .slice(0, 2)
    .map(([k, v]) => {
      const val = typeof v === "string" ? (v.length > 20 ? `${v.slice(0, 20)}...` : v) : String(v);
      return `${k}: ${val}`;
    });

  return (
    <div
      className={css({
        minWidth: "180px",
        maxWidth: "220px",
        background: "#ffffff",
        border: "1px solid #d4d2cd",
        borderRadius: "6px",
        overflow: "visible",
        boxShadow: "0 1px 3px rgba(0,0,0,0.08)",
        transition: "box-shadow 0.15s",
        position: "relative",
      })}
      style={selected ? { boxShadow: `0 0 0 2px ${color || "#c45d2c"}` } : undefined}
    >
      {/* Input handle */}
      {!isStart && (
        <Handle
          type="target"
          position={Position.Top}
          className={css({
            width: "10px",
            height: "10px",
            background: "#d4d2cd",
            border: "2px solid #ffffff",
          })}
        />
      )}

      {/* Header */}
      <div
        className={css({
          padding: "6px 10px",
          fontSize: "11px",
          fontWeight: 600,
          color: "#ffffff",
          letterSpacing: "-0.02em",
        })}
        style={{ background: color || "#4a4a52" }}
      >
        {label}
      </div>

      {/* Config preview */}
      {configPreview.length > 0 && (
        <div className={css({ padding: "6px 10px" })}>
          {configPreview.map((line, i) => (
            <div
              key={`preview-${i}`}
              className={css({
                fontSize: "10px",
                color: "#8e8e96",
                fontFamily: "'JetBrains Mono', monospace",
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              })}
            >
              {line}
            </div>
          ))}
        </div>
      )}

      {/* Output handles */}
      {!isTerminal && !hasBranching && (
        <Handle
          type="source"
          position={Position.Bottom}
          className={css({
            width: "10px",
            height: "10px",
            background: "#d4d2cd",
            border: "2px solid #ffffff",
          })}
        />
      )}

      {hasBranching && (
        <div
          className={css({
            display: "flex",
            flexWrap: "wrap",
            gap: "2px",
            padding: "4px 6px 6px",
            borderTop: "1px solid #e6e4e0",
          })}
        >
          {outputHandles.map((handle) => (
            <div
              key={handle.id}
              className={css({
                position: "relative",
                display: "flex",
                alignItems: "center",
                fontSize: "9px",
                color: "#4a4a52",
                background: "#f0eeeb",
                borderRadius: "3px",
                padding: "2px 6px",
                paddingBottom: "8px",
              })}
            >
              {handle.label}
              <Handle
                type="source"
                position={Position.Bottom}
                id={handle.id}
                className={css({
                  width: "8px",
                  height: "8px",
                  background: color || "#d4d2cd",
                  border: "2px solid #ffffff",
                })}
                style={{
                  position: "absolute",
                  bottom: "-4px",
                  left: "50%",
                  transform: "translateX(-50%)",
                }}
              />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
