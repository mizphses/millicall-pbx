import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createFileRoute, Link, redirect } from "@tanstack/react-router";
import { css } from "../../styled-system/css";
import { DataTable } from "../components/DataTable";
import { PageHead } from "../components/PageHead";
import { Tag } from "../components/Tag";
import { api } from "../lib/api";

export const Route = createFileRoute("/workflows")({
  beforeLoad: ({ context }) => {
    if (!context.auth.isAuthenticated) throw redirect({ to: "/login" });
  },
  component: WorkflowsPage,
});

interface Workflow {
  id: number;
  name: string;
  number: string;
  description: string;
  workflow_type: string;
  enabled: boolean;
  node_count: number;
}

const btnPrimary = css({
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
  textDecoration: "none",
  _hover: { background: "#a84e24" },
});

const btnEdit = css({
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
});

const btnDelete = css({
  display: "inline-flex",
  alignItems: "center",
  paddingInline: "10px",
  paddingBlock: "4px",
  fontSize: "12px",
  fontWeight: 500,
  borderRadius: "5px",
  background: "transparent",
  color: "#b83232",
  border: "1px solid",
  borderColor: "#d4d2cd",
  cursor: "pointer",
  _hover: { background: "#fce8e8", borderColor: "#b83232" },
});

const typeLabels: Record<string, { label: string; variant: "info" | "muted" }> = {
  ivr: { label: "IVR", variant: "info" },
  ai_call: { label: "AI", variant: "muted" },
};

function WorkflowsPage() {
  const queryClient = useQueryClient();

  const { data: workflows = [], isLoading } = useQuery({
    queryKey: ["workflows"],
    queryFn: () => api.get<Workflow[]>("/workflows"),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.delete(`/workflows/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["workflows"] }),
  });

  if (isLoading) return <p className={css({ color: "#4a4a52" })}>読み込み中...</p>;

  return (
    <>
      <PageHead
        title="ワークフロー"
        subtitle="IVR・AIコールのワークフローを管理します"
        actions={
          <Link to="/workflows/new" className={btnPrimary}>
            追加
          </Link>
        }
      />

      <DataTable
        columns={[
          {
            header: "名前",
            accessor: (w) => <strong>{w.name}</strong>,
          },
          {
            header: "内線番号",
            accessor: (w) => (
              <code
                className={css({
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: "12px",
                  background: "#e6e4e0",
                  padding: "2px 6px",
                  borderRadius: "3px",
                })}
              >
                {w.number}
              </code>
            ),
          },
          {
            header: "タイプ",
            accessor: (w) => {
              const t = typeLabels[w.workflow_type];
              return t ? <Tag variant={t.variant}>{t.label}</Tag> : w.workflow_type;
            },
          },
          {
            header: "ノード数",
            accessor: (w) => w.node_count ?? 0,
          },
          {
            header: "状態",
            accessor: (w) =>
              w.enabled ? <Tag variant="ok">有効</Tag> : <Tag variant="ng">無効</Tag>,
          },
          {
            header: "",
            className: css({ textAlign: "right", whiteSpace: "nowrap" }),
            accessor: (w) => (
              <div className={css({ display: "flex", justifyContent: "flex-end", gap: "4px" })}>
                <Link
                  to="/workflows/$workflowId/edit"
                  params={{ workflowId: String(w.id) }}
                  className={btnEdit}
                >
                  編集
                </Link>
                <button
                  type="button"
                  onClick={() => {
                    if (confirm(`ワークフロー「${w.name}」を削除しますか？`))
                      deleteMutation.mutate(w.id);
                  }}
                  className={btnDelete}
                >
                  削除
                </button>
              </div>
            ),
          },
        ]}
        data={workflows}
        emptyMessage="ワークフローがまだ登録されていません"
        emptyAction={
          <Link to="/workflows/new" className={btnPrimary}>
            登録する
          </Link>
        }
      />
    </>
  );
}
