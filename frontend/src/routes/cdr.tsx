import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createFileRoute, redirect } from "@tanstack/react-router";
import { useState } from "react";
import { css } from "../../styled-system/css";
import { DataTable } from "../components/DataTable";
import { PageHead } from "../components/PageHead";
import { Pagination } from "../components/Pagination";
import { Tag } from "../components/Tag";
import { $api, fetchClient } from "../lib/client";

export const Route = createFileRoute("/cdr")({
  beforeLoad: ({ context }) => {
    if (!context.auth.isAuthenticated) throw redirect({ to: "/login" });
  },
  component: CdrPage,
});

interface CDR {
  id: number;
  call_date: string;
  src: string;
  dst: string;
  dcontext: string;
  duration: number;
  billsec: number;
  disposition: string;
}

interface PagedResponse {
  total: number;
  limit: number;
  offset: number;
  items: CDR[];
}

function formatDateTime(s: string) {
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

function dispositionTag(disp: string) {
  switch (disp) {
    case "ANSWERED":
      return <Tag variant="ok">応答</Tag>;
    case "NO ANSWER":
      return <Tag variant="ng">不応答</Tag>;
    case "BUSY":
      return <Tag variant="muted">話中</Tag>;
    case "FAILED":
      return <Tag variant="ng">失敗</Tag>;
    default:
      return <Tag variant="muted">{disp}</Tag>;
  }
}

const codeStyle = css({
  fontFamily: "'JetBrains Mono', monospace",
  fontSize: "12px",
  background: "#e6e4e0",
  paddingInline: "6px",
  paddingBlock: "2px",
  borderRadius: "3px",
});

const PAGE_SIZE = 50;

function CdrPage() {
  const queryClient = useQueryClient();
  const [offset, setOffset] = useState(0);

  const { data, isLoading } = useQuery({
    queryKey: ["cdr", offset],
    queryFn: async () => {
      const { data } = await fetchClient.GET("/api/cdr", {
        params: { query: { limit: PAGE_SIZE, offset } } as never,
      });
      return data as PagedResponse | undefined;
    },
  });

  const importMutation = $api.useMutation("post", "/api/cdr/import", {
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ["cdr"] });
      setOffset(0);
      const r = result as { imported: number; csv_exists: boolean } | undefined;
      if (r && !r.csv_exists) {
        alert("CDR CSVファイルが見つかりません。");
      } else if (r && r.imported === 0) {
        alert("新しいCDRレコードはありませんでした。");
      }
    },
  });

  if (isLoading) return <p className={css({ color: "#4a4a52" })}>読み込み中...</p>;

  const cdrs = data?.items ?? [];
  const total = data?.total ?? 0;

  return (
    <>
      <PageHead
        title="発着信記録"
        subtitle={`Asterisk CDR（${total}件）`}
        actions={
          <button
            type="button"
            onClick={() => importMutation.mutate({})}
            disabled={importMutation.isPending}
            className={css({
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              paddingInline: "14px",
              paddingBlock: "6px",
              fontSize: "13px",
              fontWeight: 500,
              borderRadius: "5px",
              background: "#c45d2c",
              color: "#ffffff",
              cursor: "pointer",
              border: "none",
              _hover: { background: "#a84e24" },
              _disabled: { opacity: 0.5 },
            })}
          >
            {importMutation.isPending ? "インポート中..." : "CDRインポート"}
          </button>
        }
      />

      <DataTable
        columns={[
          {
            header: "日時",
            sortValue: (cdr) => cdr.call_date,
            accessor: (cdr) => formatDateTime(cdr.call_date),
          },
          {
            header: "発信元",
            sortValue: (cdr) => cdr.src,
            accessor: (cdr) => (cdr.src ? <code className={codeStyle}>{cdr.src}</code> : "-"),
          },
          {
            header: "宛先",
            sortValue: (cdr) => cdr.dst,
            accessor: (cdr) => (cdr.dst ? <code className={codeStyle}>{cdr.dst}</code> : "-"),
          },
          {
            header: "コンテキスト",
            sortValue: (cdr) => cdr.dcontext,
            accessor: (cdr) => <code className={codeStyle}>{cdr.dcontext}</code>,
          },
          {
            header: "呼出秒",
            sortValue: (cdr) => cdr.duration,
            accessor: (cdr) => (
              <span
                className={css({ fontFamily: "'JetBrains Mono', monospace", fontSize: "12px" })}
              >
                {cdr.duration}
              </span>
            ),
          },
          {
            header: "通話秒",
            sortValue: (cdr) => cdr.billsec,
            accessor: (cdr) => (
              <span
                className={css({ fontFamily: "'JetBrains Mono', monospace", fontSize: "12px" })}
              >
                {cdr.billsec}
              </span>
            ),
          },
          {
            header: "結果",
            sortValue: (cdr) => cdr.disposition,
            accessor: (cdr) => dispositionTag(cdr.disposition),
          },
        ]}
        data={cdrs}
        emptyMessage="CDRデータがありません。インポートを実行してください。"
      />

      <Pagination total={total} limit={PAGE_SIZE} offset={offset} onPageChange={setOffset} />
    </>
  );
}
