import { useQuery } from "@tanstack/react-query";
import { createFileRoute, Link, redirect } from "@tanstack/react-router";
import { css } from "../../styled-system/css";
import { PageHead } from "../components/PageHead";
import { api } from "../lib/api";

export const Route = createFileRoute("/call-history_/$logId")({
  beforeLoad: ({ context }) => {
    if (!context.auth.isAuthenticated) throw redirect({ to: "/login" });
  },
  component: CallHistoryDetailPage,
});

interface CallMessage {
  id: number;
  role: string;
  content: string;
  turn: number;
  created_at: string | null;
}

interface CallLogDetail {
  id: number;
  agent_id: number;
  agent_name: string;
  extension_number: string;
  caller_channel: string;
  started_at: string | null;
  ended_at: string | null;
  turn_count: number;
  messages: CallMessage[];
}

function formatDateTime(s: string | null) {
  if (!s) return "-";
  const d = new Date(s);
  return d.toLocaleString("ja-JP", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

const metaLabel = css({
  color: "#8e8e96",
  fontSize: "11px",
  textTransform: "uppercase",
  fontWeight: 600,
  marginBottom: "4px",
});

const codeStyle = css({
  fontFamily: "'JetBrains Mono', monospace",
  fontSize: "12px",
  background: "#e6e4e0",
  paddingInline: "6px",
  paddingBlock: "2px",
  borderRadius: "3px",
});

function CallHistoryDetailPage() {
  const { logId } = Route.useParams();

  const { data } = useQuery({
    queryKey: ["call-log", logId],
    queryFn: () => api.get<CallLogDetail>(`/call-history/${logId}`),
  });

  if (!data) return <p className={css({ color: "#4a4a52" })}>読み込み中...</p>;

  const log = data;
  const messages = data.messages ?? [];

  return (
    <>
      <PageHead
        title="通話詳細"
        subtitle={`${log.agent_name} - ${formatDateTime(log.started_at)}`}
        actions={
          <Link
            to="/call-history"
            className={css({
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              paddingInline: "14px",
              paddingBlock: "6px",
              fontSize: "13px",
              fontWeight: 500,
              borderRadius: "5px",
              background: "#ffffff",
              color: "#1b1b1f",
              border: "1px solid",
              borderColor: "#d4d2cd",
              textDecoration: "none",
              _hover: { background: "#e6e4e0" },
            })}
          >
            一覧に戻る
          </Link>
        }
      />

      <div
        className={css({
          background: "#ffffff",
          border: "1px solid",
          borderColor: "#d4d2cd",
          borderRadius: "5px",
          padding: "20px",
          marginBottom: "20px",
        })}
      >
        <div
          className={css({
            display: "grid",
            gridTemplateColumns: "repeat(2, 1fr)",
            gap: "16px",
            fontSize: "13px",
            sm: { gridTemplateColumns: "repeat(4, 1fr)" },
          })}
        >
          <div>
            <div className={metaLabel}>エージェント</div>
            <div>{log.agent_name}</div>
          </div>
          <div>
            <div className={metaLabel}>内線番号</div>
            <div>
              <code className={codeStyle}>{log.extension_number}</code>
            </div>
          </div>
          <div>
            <div className={metaLabel}>開始</div>
            <div>{formatDateTime(log.started_at)}</div>
          </div>
          <div>
            <div className={metaLabel}>終了</div>
            <div>{formatDateTime(log.ended_at)}</div>
          </div>
        </div>
      </div>

      <h2 className={css({ fontSize: "15px", fontWeight: 600, marginBottom: "12px" })}>会話内容</h2>

      {messages.length === 0 ? (
        <div
          className={css({
            background: "#ffffff",
            border: "1px solid",
            borderColor: "#d4d2cd",
            borderRadius: "5px",
            padding: "32px",
            textAlign: "center",
            color: "#4a4a52",
          })}
        >
          メッセージがありません
        </div>
      ) : (
        <div className={css({ display: "flex", flexDirection: "column", gap: "12px" })}>
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={css({
                padding: "16px",
                borderRadius: "5px",
                border: "1px solid",
                ...(msg.role === "assistant"
                  ? { background: "#fdf3ee", borderColor: "rgba(196, 93, 44, 0.2)", marginLeft: "0", marginRight: "32px" }
                  : { background: "#ffffff", borderColor: "#d4d2cd", marginLeft: "32px", marginRight: "0" }),
              })}
            >
              <div className={css({ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" })}>
                <span
                  className={css({
                    fontSize: "11px",
                    fontWeight: 600,
                    color: "#8e8e96",
                    textTransform: "uppercase",
                  })}
                >
                  {msg.role === "assistant" ? "AI" : "ユーザー"}
                </span>
                <span className={css({ fontSize: "11px", color: "#8e8e96" })}>
                  ターン {msg.turn}
                </span>
              </div>
              <div className={css({ fontSize: "13px", whiteSpace: "pre-wrap" })}>{msg.content}</div>
            </div>
          ))}
        </div>
      )}
    </>
  );
}
