import { css } from "../../../styled-system/css";
import type { ConfigField, NodeTypeDefinition } from "./NodePalette";

interface NodeInspectorProps {
  nodeId: string;
  nodeType: NodeTypeDefinition | undefined;
  config: Record<string, unknown>;
  onConfigChange: (nodeId: string, config: Record<string, unknown>) => void;
  onClose: () => void;
}

const labelStyle = css({
  display: "block",
  fontSize: "12px",
  fontWeight: 600,
  color: "#4a4a52",
  marginBottom: "4px",
});

const inputStyle = css({
  width: "100%",
  paddingInline: "8px",
  paddingBlock: "6px",
  fontSize: "13px",
  color: "#1b1b1f",
  background: "#ffffff",
  border: "1px solid #d4d2cd",
  borderRadius: "5px",
  outline: "none",
  _focus: { borderColor: "#c45d2c" },
});

const textareaStyle = css({
  width: "100%",
  paddingInline: "8px",
  paddingBlock: "6px",
  fontSize: "13px",
  color: "#1b1b1f",
  background: "#ffffff",
  border: "1px solid #d4d2cd",
  borderRadius: "5px",
  outline: "none",
  minHeight: "80px",
  resize: "vertical",
  fontFamily: "inherit",
  _focus: { borderColor: "#c45d2c" },
});

const selectStyle = css({
  width: "100%",
  paddingInline: "8px",
  paddingBlock: "6px",
  fontSize: "13px",
  color: "#1b1b1f",
  background: "#ffffff",
  border: "1px solid #d4d2cd",
  borderRadius: "5px",
  outline: "none",
  _focus: { borderColor: "#c45d2c" },
});

const checkboxLabel = css({
  display: "inline-flex",
  alignItems: "center",
  gap: "6px",
  fontSize: "13px",
  cursor: "pointer",
});

const checkboxInput = css({
  width: "14px",
  height: "14px",
  accentColor: "#c45d2c",
});

export function NodeInspector({
  nodeId,
  nodeType,
  config,
  onConfigChange,
  onClose,
}: NodeInspectorProps) {
  function updateField(name: string, value: unknown) {
    onConfigChange(nodeId, { ...config, [name]: value });
  }

  if (!nodeType) {
    return (
      <div
        className={css({
          width: "320px",
          minWidth: "320px",
          background: "#ffffff",
          borderLeft: "1px solid #d4d2cd",
          padding: "16px",
          flexShrink: 0,
        })}
      >
        <p className={css({ color: "#8e8e96", fontSize: "13px" })}>ノード情報が見つかりません</p>
      </div>
    );
  }

  return (
    <div
      className={css({
        width: "320px",
        minWidth: "320px",
        background: "#ffffff",
        borderLeft: "1px solid #d4d2cd",
        overflowY: "auto",
        flexShrink: 0,
        display: "flex",
        flexDirection: "column",
      })}
    >
      <div
        className={css({
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "12px 16px",
          borderBottom: "1px solid #e6e4e0",
        })}
      >
        <div>
          <div
            className={css({
              fontSize: "14px",
              fontWeight: 700,
              color: "#1b1b1f",
            })}
          >
            {nodeType.label}
          </div>
          <div
            className={css({
              fontSize: "11px",
              color: "#8e8e96",
              fontFamily: "'JetBrains Mono', monospace",
            })}
          >
            {nodeType.type}
          </div>
        </div>
        <button
          type="button"
          onClick={onClose}
          className={css({
            background: "transparent",
            border: "none",
            cursor: "pointer",
            color: "#8e8e96",
            fontSize: "18px",
            padding: "4px",
            lineHeight: 1,
            _hover: { color: "#1b1b1f" },
          })}
        >
          &times;
        </button>
      </div>

      <div className={css({ padding: "16px", flex: 1 })}>
        {nodeType.config_schema.length === 0 ? (
          <p className={css({ color: "#8e8e96", fontSize: "13px" })}>設定項目はありません</p>
        ) : (
          nodeType.config_schema.map((field) => (
            <div key={field.name} className={css({ marginBottom: "14px" })}>
              <InspectorField
                field={field}
                value={config[field.name]}
                onChange={(v) => updateField(field.name, v)}
              />
            </div>
          ))
        )}
      </div>
    </div>
  );
}

function InspectorField({
  field,
  value,
  onChange,
}: {
  field: ConfigField;
  value: unknown;
  onChange: (v: unknown) => void;
}) {
  switch (field.type) {
    case "string":
      return (
        <div>
          <label className={labelStyle}>{field.label}</label>
          <input
            type="text"
            className={inputStyle}
            value={(value as string) ?? ""}
            onChange={(e) => onChange(e.target.value)}
            placeholder={field.placeholder}
          />
        </div>
      );

    case "textarea":
      return (
        <div>
          <label className={labelStyle}>{field.label}</label>
          <textarea
            className={textareaStyle}
            value={(value as string) ?? ""}
            onChange={(e) => onChange(e.target.value)}
            placeholder={field.placeholder}
          />
        </div>
      );

    case "number":
      return (
        <div>
          <label className={labelStyle}>{field.label}</label>
          <input
            type="number"
            className={inputStyle}
            value={(value as number) ?? ""}
            onChange={(e) => onChange(e.target.value === "" ? "" : Number(e.target.value))}
            placeholder={field.placeholder}
          />
        </div>
      );

    case "boolean":
      return (
        <label className={checkboxLabel}>
          <input
            type="checkbox"
            className={checkboxInput}
            checked={Boolean(value)}
            onChange={(e) => onChange(e.target.checked)}
          />
          {field.label}
        </label>
      );

    case "select":
      return (
        <div>
          <label className={labelStyle}>{field.label}</label>
          <select
            className={selectStyle}
            value={(value as string) ?? ""}
            onChange={(e) => onChange(e.target.value)}
          >
            <option value="">-- 選択 --</option>
            {(field.options || []).map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
      );

    case "multi_select":
      return (
        <div>
          <label className={labelStyle}>{field.label}</label>
          <div className={css({ display: "flex", flexDirection: "column", gap: "4px" })}>
            {(field.options || []).map((opt) => {
              const selected = Array.isArray(value)
                ? (value as string[]).includes(opt.value)
                : false;
              return (
                <label key={opt.value} className={checkboxLabel}>
                  <input
                    type="checkbox"
                    className={checkboxInput}
                    checked={selected}
                    onChange={(e) => {
                      const current = Array.isArray(value) ? (value as string[]) : [];
                      if (e.target.checked) {
                        onChange([...current, opt.value]);
                      } else {
                        onChange(current.filter((v) => v !== opt.value));
                      }
                    }}
                  />
                  {opt.label}
                </label>
              );
            })}
          </div>
        </div>
      );

    case "key_value_list":
      return <KeyValueListField field={field} value={value} onChange={onChange} />;

    case "json":
      return (
        <div>
          <label className={labelStyle}>{field.label}</label>
          <textarea
            className={css({
              width: "100%",
              paddingInline: "8px",
              paddingBlock: "6px",
              fontSize: "12px",
              color: "#1b1b1f",
              background: "#ffffff",
              border: "1px solid #d4d2cd",
              borderRadius: "5px",
              outline: "none",
              minHeight: "100px",
              resize: "vertical",
              fontFamily: "'JetBrains Mono', monospace",
              _focus: { borderColor: "#c45d2c" },
            })}
            value={typeof value === "string" ? value : JSON.stringify(value ?? {}, null, 2)}
            onChange={(e) => {
              try {
                onChange(JSON.parse(e.target.value));
              } catch {
                onChange(e.target.value);
              }
            }}
            placeholder="{}"
          />
        </div>
      );

    default:
      return (
        <div>
          <label className={labelStyle}>{field.label}</label>
          <input
            type="text"
            className={inputStyle}
            value={String(value ?? "")}
            onChange={(e) => onChange(e.target.value)}
          />
        </div>
      );
  }
}

function KeyValueListField({
  field,
  value,
  onChange,
}: {
  field: ConfigField;
  value: unknown;
  onChange: (v: unknown) => void;
}) {
  const pairs: { key: string; value: string }[] = Array.isArray(value)
    ? (value as { key: string; value: string }[])
    : [];

  function updatePair(index: number, k: string, v: string) {
    const next = [...pairs];
    next[index] = { key: k, value: v };
    onChange(next);
  }

  function addPair() {
    onChange([...pairs, { key: "", value: "" }]);
  }

  function removePair(index: number) {
    onChange(pairs.filter((_, i) => i !== index));
  }

  return (
    <div>
      <label className={labelStyle}>{field.label}</label>
      {pairs.map((pair, i) => (
        <div
          key={i}
          className={css({
            display: "flex",
            gap: "4px",
            marginBottom: "4px",
            alignItems: "center",
          })}
        >
          <input
            type="text"
            className={css({
              flex: 1,
              paddingInline: "6px",
              paddingBlock: "4px",
              fontSize: "12px",
              border: "1px solid #d4d2cd",
              borderRadius: "3px",
              outline: "none",
              _focus: { borderColor: "#c45d2c" },
            })}
            value={pair.key}
            onChange={(e) => updatePair(i, e.target.value, pair.value)}
            placeholder="キー"
          />
          <input
            type="text"
            className={css({
              flex: 1,
              paddingInline: "6px",
              paddingBlock: "4px",
              fontSize: "12px",
              border: "1px solid #d4d2cd",
              borderRadius: "3px",
              outline: "none",
              _focus: { borderColor: "#c45d2c" },
            })}
            value={pair.value}
            onChange={(e) => updatePair(i, pair.key, e.target.value)}
            placeholder="値"
          />
          <button
            type="button"
            onClick={() => removePair(i)}
            className={css({
              background: "transparent",
              border: "none",
              color: "#b83232",
              cursor: "pointer",
              fontSize: "16px",
              padding: "2px 4px",
              lineHeight: 1,
              _hover: { background: "#fce8e8", borderRadius: "3px" },
            })}
          >
            &times;
          </button>
        </div>
      ))}
      <button
        type="button"
        onClick={addPair}
        className={css({
          fontSize: "12px",
          fontWeight: 500,
          color: "#c45d2c",
          background: "transparent",
          border: "none",
          cursor: "pointer",
          padding: "4px 0",
          _hover: { textDecoration: "underline" },
        })}
      >
        + 追加
      </button>
    </div>
  );
}
