import { css } from "../../../styled-system/css";

export interface NodeTypeDefinition {
  type: string;
  label: string;
  category: string;
  color: string;
  config_schema: ConfigField[];
}

export interface ConfigField {
  name: string;
  label: string;
  type: "string" | "textarea" | "number" | "boolean" | "select" | "multi_select" | "key_value_list" | "json";
  required?: boolean;
  default?: unknown;
  options?: { value: string; label: string }[];
  placeholder?: string;
}

interface NodePaletteProps {
  nodeTypes: NodeTypeDefinition[];
}

const categoryLabels: Record<string, string> = {
  common: "共通ノード",
  ivr: "IVRノード",
  ai: "AIワークフローノード",
};

export function NodePalette({ nodeTypes }: NodePaletteProps) {
  const grouped = nodeTypes.reduce(
    (acc, nt) => {
      const cat = nt.category || "common";
      if (!acc[cat]) acc[cat] = [];
      acc[cat].push(nt);
      return acc;
    },
    {} as Record<string, NodeTypeDefinition[]>,
  );

  function onDragStart(e: React.DragEvent, nodeType: NodeTypeDefinition) {
    e.dataTransfer.setData("application/millicall-node", JSON.stringify(nodeType));
    e.dataTransfer.effectAllowed = "move";
  }

  return (
    <div
      className={css({
        width: "240px",
        minWidth: "240px",
        background: "#ffffff",
        borderRight: "1px solid #d4d2cd",
        overflowY: "auto",
        padding: "12px",
        flexShrink: 0,
      })}
    >
      <div
        className={css({
          fontSize: "11px",
          fontWeight: 600,
          color: "#8e8e96",
          textTransform: "uppercase",
          letterSpacing: "0.03em",
          marginBottom: "12px",
        })}
      >
        ノードパレット
      </div>

      {Object.entries(grouped).map(([category, types]) => (
        <div key={category} className={css({ marginBottom: "16px" })}>
          <div
            className={css({
              fontSize: "12px",
              fontWeight: 600,
              color: "#4a4a52",
              marginBottom: "8px",
              paddingBottom: "4px",
              borderBottom: "1px solid #e6e4e0",
            })}
          >
            {categoryLabels[category] || category}
          </div>
          {types.map((nt) => (
            <div
              key={nt.type}
              draggable
              onDragStart={(e) => onDragStart(e, nt)}
              className={css({
                display: "flex",
                alignItems: "center",
                gap: "8px",
                padding: "8px 10px",
                marginBottom: "4px",
                borderRadius: "5px",
                border: "1px solid #e6e4e0",
                cursor: "grab",
                fontSize: "13px",
                fontWeight: 500,
                color: "#1b1b1f",
                background: "#ffffff",
                _hover: { background: "#faf9f7", borderColor: "#d4d2cd" },
                _active: { cursor: "grabbing" },
              })}
            >
              <div
                className={css({
                  width: "4px",
                  height: "20px",
                  borderRadius: "2px",
                  flexShrink: 0,
                })}
                style={{ background: nt.color }}
              />
              {nt.label}
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}
