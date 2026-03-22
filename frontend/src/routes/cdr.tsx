import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createFileRoute, redirect } from "@tanstack/react-router";
import { css } from "../../styled-system/css";
import { DataTable } from "../components/DataTable";
import { PageHead } from "../components/PageHead";
import { Tag } from "../components/Tag";
import { api } from "../lib/api";

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

function CdrPage() {
  const queryClient = useQueryClient();

  const { data: cdrs = [], isLoading } = useQuery({
    queryKey: ["cdr"],
    queryFn: () => api.get<CDR[]>("/cdr"),
  });

  const importMutation = useMutation({
    mutationFn: () => api.post("/cdr/import"),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["cdr"] }),
  });

  if (isLoading) return <p className={css({ color: "#4a4a52" })}>読み込み中...</p>;

  return (
    <>
      <PageHead
        title="発着信記録"
        subtitle="Asterisk CDR（通話詳細記録）を表示します"
        actions={
          <button
            onClick={() => importMutation.mutate()}
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
              _hover: { background: "#a84e24" },
              _disabled: { opacity: "0.5" },
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
            accessor: (cdr) => formatDateTime(cdr.call_date),
          },
          {
            header: "発信元",
            accessor: (cdr) => cdr.src || "-",
          },
          {
            header: "宛先",
            accessor: (cdr) => cdr.dst || "-",
          },
          {
            header: "コンテキスト",
            accessor: (cdr) => <code className={codeStyle}>{cdr.dcontext}</code>,
          },
          {
            header: "呼出秒",
            accessor: (cdr) => (
              <span className={css({ fontFamily: "'JetBrains Mono', monospace", fontSize: "12px" })}>{cdr.duration}</span>
            ),
          },
          {
            header: "通話秒",
            accessor: (cdr) => (
              <span className={css({ fontFamily: "'JetBrains Mono', monospace", fontSize: "12px" })}>{cdr.billsec}</span>
            ),
          },
          {
            header: "結果",
            accessor: (cdr) => dispositionTag(cdr.disposition),
          },
        ]}
        data={cdrs}
        emptyMessage="CDRデータがありません。インポートを実行してください。"
      />
    </>
  );
}
