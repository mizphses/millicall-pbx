import { useQuery } from "@tanstack/react-query";
import { createFileRoute, Link, redirect } from "@tanstack/react-router";
import { css } from "../../styled-system/css";
import { DataTable } from "../components/DataTable";
import { PageHead } from "../components/PageHead";
import { api } from "../lib/api";

export const Route = createFileRoute("/call-history")({
  beforeLoad: ({ context }) => {
    if (!context.auth.isAuthenticated) throw redirect({ to: "/login" });
  },
  component: CallHistoryPage,
});

interface CallLog {
  id: number;
  agent_name: string;
  extension_number: string;
  caller_channel: string;
  started_at: string | null;
  ended_at: string | null;
  turn_count: number;
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

const codeStyle = css({
  fontFamily: "'JetBrains Mono', monospace",
  fontSize: "12px",
  background: "#e6e4e0",
  paddingInline: "6px",
  paddingBlock: "2px",
  borderRadius: "3px",
});

function CallHistoryPage() {
  const { data: logs = [], isLoading } = useQuery({
    queryKey: ["call-history"],
    queryFn: () => api.get<CallLog[]>("/call-history"),
  });

  if (isLoading) return <p className={css({ color: "#4a4a52" })}>読み込み中...</p>;

  return (
    <>
      <PageHead title="AI通話履歴" subtitle="AIエージェントの通話記録を確認できます" />

      <DataTable
        columns={[
          {
            header: "日時",
            accessor: (log) => formatDateTime(log.started_at),
          },
          {
            header: "エージェント",
            accessor: (log) => log.agent_name,
          },
          {
            header: "内線番号",
            accessor: (log) => <code className={codeStyle}>{log.extension_number}</code>,
          },
          {
            header: "発信元",
            accessor: (log) => log.caller_channel,
          },
          {
            header: "ターン数",
            accessor: (log) => (
              <span className={css({ fontFamily: "'JetBrains Mono', monospace" })}>{log.turn_count}</span>
            ),
          },
          {
            header: "",
            className: css({ textAlign: "right" }),
            accessor: (log) => (
              <Link
                to="/call-history/$logId"
                params={{ logId: String(log.id) }}
                className={css({
                  display: "inline-flex",
                  alignItems: "center",
                  paddingInline: "10px",
                  paddingBlock: "4px",
                  fontSize: "12px",
                  fontWeight: 500,
                  borderRadius: "5px",
                  background: "transparent",
                  color: "#4a4a52",
                  textDecoration: "none",
                  _hover: { background: "#e6e4e0" },
                })}
              >
                詳細
              </Link>
            ),
          },
        ]}
        data={logs}
        emptyMessage="通話履歴がまだありません"
      />
    </>
  );
}
