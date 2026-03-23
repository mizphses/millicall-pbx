import { useQuery } from "@tanstack/react-query";
import { createFileRoute, redirect } from "@tanstack/react-router";
import { css } from "../../styled-system/css";
import { PageHead } from "../components/PageHead";
import { Tag } from "../components/Tag";
import { api } from "../lib/api";

export const Route = createFileRoute("/mcp-guide")({
  beforeLoad: ({ context }) => {
    if (!context.auth.isAuthenticated) throw redirect({ to: "/login" });
  },
  component: McpGuidePage,
});

interface TrunkInfo {
  name: string;
  display_name: string;
  did_number: string;
  caller_id: string;
  prefix_rules: { prefix: string; prepend: string; example: string }[];
  has_prefix: boolean;
}

interface McpConfig {
  remote_config: Record<string, unknown>;
  stdio_config: Record<string, unknown>;
  available_tools: { name: string; description: string; category: string }[];
  current_extensions: { number: string; name: string; type: string }[];
  current_trunks: { name: string; display_name: string; did: string; prefixes: string }[];
  conversation_examples: { title: string; steps: string[] }[];
}

interface OutboundGuide {
  trunks: TrunkInfo[];
  dialing_rules: Record<string, string>;
}

const section = css({
  background: "#ffffff",
  border: "1px solid #d4d2cd",
  borderRadius: "6px",
  padding: "24px",
  marginBottom: "20px",
});

const heading2 = css({ fontSize: "17px", fontWeight: 700, color: "#1b1b1f", marginBottom: "12px" });
const heading3 = css({ fontSize: "14px", fontWeight: 600, color: "#4a4a52", marginTop: "20px", marginBottom: "8px" });
const paragraph = css({ fontSize: "14px", lineHeight: "1.7", color: "#4a4a52", marginBottom: "12px" });

const codeBlock = css({
  background: "#262630",
  color: "#e6e4e0",
  padding: "16px",
  borderRadius: "6px",
  fontSize: "13px",
  fontFamily: "'JetBrains Mono', monospace",
  overflowX: "auto",
  marginBottom: "12px",
  lineHeight: "1.6",
  whiteSpace: "pre",
});

const inlineCode = css({
  fontFamily: "'JetBrains Mono', monospace",
  fontSize: "12px",
  background: "#f3f2ef",
  color: "#1b1b1f",
  paddingInline: "5px",
  paddingBlock: "2px",
  borderRadius: "3px",
});

const thStyle = css({
  paddingInline: "14px",
  paddingBlock: "10px",
  textAlign: "left",
  fontSize: "11px",
  fontWeight: 600,
  color: "#8e8e96",
  textTransform: "uppercase",
  background: "#faf9f7",
  borderBottom: "1px solid #d4d2cd",
});

const tdStyle = css({
  paddingInline: "14px",
  paddingBlock: "10px",
  borderBottom: "1px solid #e6e4e0",
  verticalAlign: "middle",
});

const tableWrap = css({
  border: "1px solid #d4d2cd",
  borderRadius: "5px",
  overflowX: "auto",
  marginBottom: "12px",
});

const tableStyle = css({ width: "100%", borderCollapse: "collapse", fontSize: "13px" });
const toolName = css({ fontFamily: "'JetBrains Mono', monospace", fontSize: "12px", fontWeight: 600, color: "#c45d2c" });

const noteBox = css({
  background: "#fef3c7",
  border: "1px solid #f59e0b",
  borderRadius: "6px",
  padding: "12px 16px",
  fontSize: "13px",
  lineHeight: "1.6",
  color: "#92400e",
  marginBottom: "12px",
});

function McpGuidePage() {
  const { data: mcpConfig } = useQuery({
    queryKey: ["mcp-config"],
    queryFn: () => api.get<McpConfig>("/guide/mcp-config"),
  });

  const { data: outbound } = useQuery({
    queryKey: ["outbound-guide"],
    queryFn: () => api.get<OutboundGuide>("/guide/outbound"),
  });

  const tools = mcpConfig?.available_tools ?? [];
  const categories = [...new Set(tools.map((t) => t.category))];

  return (
    <>
      <PageHead title="MCP連携ガイド" subtitle="Claude DesktopなどからMillicallを操作する方法" />

      {/* 概要 */}
      <div className={section}>
        <h2 className={heading2}>概要</h2>
        <p className={paragraph}>
          MCP（Model Context Protocol）を使うと、Claude DesktopなどのAIアシスタントからMillicall PBXを直接操作できます。
          電話の発信・通話・電話帳管理・通話転送などをテキストベースの会話で行えます。
        </p>
      </div>

      {/* 接続設定 */}
      <div className={section}>
        <h2 className={heading2}>接続設定</h2>

        <h3 className={heading3}>リモート接続（推奨）</h3>
        <p className={paragraph}>
          Streamable HTTP で接続します。<code className={inlineCode}>claude_desktop_config.json</code> に以下を追加してください。
          URLのIPアドレスはMillicallサーバーのアドレスに置き換えてください。
        </p>
        {mcpConfig && (
          <pre className={codeBlock}>
            {JSON.stringify(mcpConfig.remote_config, null, 2)}
          </pre>
        )}

        <h3 className={heading3}>stdio接続（Docker exec）</h3>
        <p className={paragraph}>
          サーバーと同じマシンで実行する場合は stdio 接続も使えます。
        </p>
        {mcpConfig && (
          <pre className={codeBlock}>
            {JSON.stringify(mcpConfig.stdio_config, null, 2)}
          </pre>
        )}
      </div>

      {/* 利用可能なツール */}
      <div className={section}>
        <h2 className={heading2}>利用可能なツール</h2>
        {categories.map((cat) => (
          <div key={cat}>
            <h3 className={heading3}>{cat}</h3>
            <div className={tableWrap}>
              <table className={tableStyle}>
                <thead>
                  <tr>
                    <th className={thStyle}>ツール</th>
                    <th className={thStyle}>説明</th>
                  </tr>
                </thead>
                <tbody>
                  {tools
                    .filter((t) => t.category === cat)
                    .map((tool) => (
                      <tr key={tool.name} className={css({ _hover: { background: "#fdf3ee" } })}>
                        <td className={tdStyle}>
                          <span className={toolName}>{tool.name}</span>
                        </td>
                        <td className={tdStyle}>{tool.description}</td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          </div>
        ))}
      </div>

      {/* 現在のシステム構成 */}
      <div className={section}>
        <h2 className={heading2}>現在のシステム構成</h2>

        <h3 className={heading3}>有効な内線</h3>
        {mcpConfig?.current_extensions?.length ? (
          <div className={css({ display: "flex", flexWrap: "wrap", gap: "6px", marginBottom: "16px" })}>
            {mcpConfig.current_extensions.map((ext) => (
              <Tag key={ext.number} variant={ext.type === "phone" ? "phone" : ext.type === "ivr" ? "ivr" : ext.type === "ai_workflow" ? "workflow" : "ai"}>
                {ext.number} - {ext.name}
              </Tag>
            ))}
          </div>
        ) : (
          <p className={paragraph}>内線が設定されていません</p>
        )}

        <h3 className={heading3}>有効なトランク</h3>
        {mcpConfig?.current_trunks?.length ? (
          <div className={tableWrap}>
            <table className={tableStyle}>
              <thead>
                <tr>
                  <th className={thStyle}>名前</th>
                  <th className={thStyle}>電話番号</th>
                  <th className={thStyle}>プレフィックス</th>
                </tr>
              </thead>
              <tbody>
                {mcpConfig.current_trunks.map((t) => (
                  <tr key={t.name}>
                    <td className={tdStyle}>{t.display_name}</td>
                    <td className={tdStyle}><code className={inlineCode}>{t.did || "-"}</code></td>
                    <td className={tdStyle}>{t.prefixes || "0発信"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className={paragraph}>トランクが設定されていません</p>
        )}
      </div>

      {/* 外線発信ガイド */}
      <div className={section}>
        <h2 className={heading2}>外線発信ガイド</h2>

        <h3 className={heading3}>ダイヤルルール</h3>
        {outbound?.dialing_rules && (
          <div className={tableWrap}>
            <table className={tableStyle}>
              <thead>
                <tr>
                  <th className={thStyle}>種別</th>
                  <th className={thStyle}>説明</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(outbound.dialing_rules).map(([key, desc]) => (
                  <tr key={key}>
                    <td className={tdStyle}><code className={inlineCode}>{key}</code></td>
                    <td className={tdStyle}>{desc}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <h3 className={heading3}>トランク別プレフィックスルール</h3>
        {outbound?.trunks?.map((trunk) => (
          <div key={trunk.name} className={css({ marginBottom: "16px" })}>
            <div className={css({ fontWeight: 600, fontSize: "13px", marginBottom: "6px" })}>
              {trunk.display_name}
              {trunk.did_number && <span className={css({ color: "#8e8e96", fontWeight: 400 })}> ({trunk.did_number})</span>}
            </div>
            {trunk.prefix_rules.length > 0 ? (
              <div className={tableWrap}>
                <table className={tableStyle}>
                  <thead>
                    <tr>
                      <th className={thStyle}>プレフィックス</th>
                      <th className={thStyle}>付加文字</th>
                      <th className={thStyle}>例</th>
                    </tr>
                  </thead>
                  <tbody>
                    {trunk.prefix_rules.map((rule, i) => (
                      <tr key={`${trunk.name}-${i}`}>
                        <td className={tdStyle}><code className={inlineCode}>{rule.prefix}</code></td>
                        <td className={tdStyle}>{rule.prepend || "-"}</td>
                        <td className={tdStyle}><code className={inlineCode}>{rule.example}</code></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className={css({ fontSize: "13px", color: "#4a4a52" })}>プレフィックスなし（0発信 / 184 / 186）</p>
            )}
          </div>
        ))}

        <div className={noteBox}>
          <strong>注意:</strong> MCP経由の発信では、<code className={inlineCode}>dial</code> ツールが番号形式を自動判定します。
          内線番号はそのまま、外線番号にはデフォルトトランクのプレフィックスが付与されます。
        </div>
      </div>

      {/* 使い方の例 */}
      <div className={section}>
        <h2 className={heading2}>使い方の例</h2>
        {mcpConfig?.conversation_examples?.map((ex, i) => (
          <div key={`example-${i}`}>
            <h3 className={heading3}>{ex.title}</h3>
            <pre className={codeBlock}>{ex.steps.join("\n")}</pre>
          </div>
        ))}
      </div>
    </>
  );
}
