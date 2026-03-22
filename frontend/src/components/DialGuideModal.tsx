import { css } from "../../styled-system/css";
import { Modal } from "./Modal";

interface Trunk {
  id: number;
  display_name: string;
  did_number: string;
  outbound_prefixes: string;
  enabled: boolean;
}

interface DialGuideModalProps {
  open: boolean;
  onClose: () => void;
  trunks: Trunk[];
}

interface PrefixRule {
  pfx: string;
  prepend: string;
}

function parsePrefixes(prefixes: string): PrefixRule[] {
  if (!prefixes) return [];
  return prefixes
    .split(",")
    .map((entry) => entry.trim())
    .filter(Boolean)
    .map((entry) => {
      if (entry.includes(":")) {
        const [pfx, prepend] = entry.split(":", 2);
        return { pfx: pfx.trim(), prepend: prepend.trim() };
      }
      return { pfx: entry, prepend: "" };
    });
}

const flexRow = css({
  display: "flex",
  alignItems: "baseline",
  gap: "8px",
  paddingBlock: "4px",
  fontSize: "13px",
});

const codeStyle = css({
  fontSize: "12px",
  background: "#e6e4e0",
  paddingInline: "6px",
  paddingBlock: "2px",
  borderRadius: "3px",
});

export function DialGuideModal({ open, onClose, trunks }: DialGuideModalProps) {
  const enabledTrunks = trunks.filter((t) => t.enabled);

  return (
    <Modal open={open} onClose={onClose} title="ダイヤルガイド">
      <p className={css({ fontSize: "13px", color: "#4a4a52", marginBottom: "16px" })}>
        SIPフォンから外線発信するときのダイヤル方法一覧です。
      </p>

      {enabledTrunks.map((trunk) => {
        const rules = parsePrefixes(trunk.outbound_prefixes);
        return (
          <div key={trunk.id} className={css({ marginBottom: "20px" })}>
            <h3
              className={css({
                fontSize: "13px",
                fontWeight: 600,
                color: "#4a4a52",
                marginBottom: "8px",
                paddingBottom: "4px",
                borderBottom: "1px solid",
                borderColor: "#e6e4e0",
              })}
            >
              {trunk.display_name}
              {trunk.did_number && ` (${trunk.did_number})`}
            </h3>

            {rules.length > 0 ? (
              rules.map((rule, i) => (
                <div key={i}>
                  <div className={flexRow}>
                    <code className={codeStyle}>{rule.pfx}</code>
                    <span>+ 番号</span>
                    <span className={css({ color: "#8e8e96", flexShrink: "0" })}>&rarr;</span>
                    {rule.prepend ? (
                      <span>
                        <code className={codeStyle}>{rule.prepend}</code> + 番号 で発信
                      </span>
                    ) : (
                      <span>番号をそのまま発信</span>
                    )}
                  </div>
                  <div
                    className={css({
                      display: "flex",
                      alignItems: "baseline",
                      gap: "8px",
                      paddingBlock: "4px",
                      fontSize: "12px",
                      color: "#4a4a52",
                      paddingLeft: "16px",
                    })}
                  >
                    <span>
                      例: <code className={codeStyle}>{rule.pfx}0312345678</code>
                    </span>
                    <span className={css({ color: "#8e8e96" })}>&rarr;</span>
                    <code className={codeStyle}>{rule.prepend}0312345678</code>
                  </div>
                </div>
              ))
            ) : (
              <>
                <div className={flexRow}>
                  <code className={codeStyle}>0</code>
                  <span>+ 番号</span>
                  <span className={css({ color: "#8e8e96" })}>&rarr;</span>
                  <span>通常発信</span>
                </div>
                <div
                  className={css({
                    display: "flex",
                    alignItems: "baseline",
                    gap: "8px",
                    paddingBlock: "4px",
                    fontSize: "12px",
                    color: "#4a4a52",
                    paddingLeft: "16px",
                  })}
                >
                  <span>
                    例: <code className={codeStyle}>0312345678</code>
                  </span>
                </div>
                <div className={flexRow}>
                  <code className={codeStyle}>184</code>
                  <span>+</span>
                  <code className={codeStyle}>0</code>
                  <span>+ 番号</span>
                  <span className={css({ color: "#8e8e96" })}>&rarr;</span>
                  <span>非通知で発信</span>
                </div>
                <div className={flexRow}>
                  <code className={codeStyle}>186</code>
                  <span>+</span>
                  <code className={codeStyle}>0</code>
                  <span>+ 番号</span>
                  <span className={css({ color: "#8e8e96" })}>&rarr;</span>
                  <span>番号通知で発信</span>
                </div>
              </>
            )}
          </div>
        );
      })}

      <hr
        className={css({
          borderTop: "1px solid",
          borderColor: "#e6e4e0",
          marginBlock: "16px",
        })}
      />
      <div className={css({ marginBottom: "16px" })}>
        <h3
          className={css({
            fontSize: "13px",
            fontWeight: 600,
            color: "#4a4a52",
            marginBottom: "8px",
            paddingBottom: "4px",
            borderBottom: "1px solid",
            borderColor: "#e6e4e0",
          })}
        >
          内線・その他
        </h3>
        <div className={css({ paddingBlock: "4px", fontSize: "13px" })}>内線番号をそのままダイヤル</div>
        <div className={flexRow}>
          <code className={codeStyle}>*43</code>
          <span className={css({ color: "#8e8e96" })}>&rarr;</span>
          <span>エコーテスト</span>
        </div>
      </div>
    </Modal>
  );
}
