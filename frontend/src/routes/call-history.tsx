import { useQuery } from "@tanstack/react-query";
import { createFileRoute, Link, redirect } from "@tanstack/react-router";
import { useState } from "react";
import { css } from "../../styled-system/css";
import { DataTable } from "../components/DataTable";
import { PageHead } from "../components/PageHead";
import { Pagination } from "../components/Pagination";
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

interface PagedResponse {
  total: number;
  limit: number;
  offset: number;
  items: CallLog[];
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

const PAGE_SIZE = 30;

function CallHistoryPage() {
  const [offset, setOffset] = useState(0);

  const { data, isLoading } = useQuery({
    queryKey: ["call-history", offset],
    queryFn: () => api.get<PagedResponse>(`/call-history?limit=${PAGE_SIZE}&offset=${offset}`),
  });

  if (isLoading) return <p className={css({ color: "#4a4a52" })}>読み込み中...</p>;

  const logs = data?.items ?? [];
  const total = data?.total ?? 0;

  return (
    <>
      <PageHead title="AI通話履歴" subtitle={`AIエージェントの通話記録（${total}件）`} />

      <DataTable
        columns={[
          {
            header: "日時",
            sortValue: (log) => log.started_at ?? "",
            accessor: (log) => formatDateTime(log.started_at),
          },
          {
            header: "エージェント",
            sortValue: (log) => log.agent_name,
            accessor: (log) => log.agent_name,
          },
          {
            header: "内線番号",
            sortValue: (log) => log.extension_number,
            accessor: (log) => <code className={codeStyle}>{log.extension_number}</code>,
          },
          {
            header: "ターン数",
            sortValue: (log) => log.turn_count,
            accessor: (log) => (
              <span className={css({ fontFamily: "'JetBrains Mono', monospace" })}>
                {log.turn_count}
              </span>
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

      <Pagination total={total} limit={PAGE_SIZE} offset={offset} onPageChange={setOffset} />
    </>
  );
}
