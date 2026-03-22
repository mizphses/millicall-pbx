import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createFileRoute, Link, redirect } from "@tanstack/react-router";
import { css } from "../../styled-system/css";
import { DataTable } from "../components/DataTable";
import { PageHead } from "../components/PageHead";
import { Tag } from "../components/Tag";
import { api } from "../lib/api";

export const Route = createFileRoute("/extensions")({
  beforeLoad: ({ context }) => {
    if (!context.auth.isAuthenticated) throw redirect({ to: "/login" });
  },
  component: ExtensionsPage,
});

interface Extension {
  id: number;
  number: string;
  display_name: string;
  type: string;
  enabled: boolean;
  peer_id: number | null;
  ai_agent_id: number | null;
}

interface Peer {
  id: number;
  username: string;
}

interface Agent {
  id: number;
  llm_provider: string;
  llm_model: string;
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

function ExtensionsPage() {
  const queryClient = useQueryClient();
  const { data: extensions = [], isLoading } = useQuery({
    queryKey: ["extensions"],
    queryFn: () => api.get<Extension[]>("/extensions"),
  });
  const { data: peers = [] } = useQuery({
    queryKey: ["peers"],
    queryFn: () => api.get<Peer[]>("/peers"),
  });
  const { data: agents = [] } = useQuery({
    queryKey: ["agents"],
    queryFn: () => api.get<Agent[]>("/agents"),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.delete(`/extensions/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["extensions"] }),
  });

  const peerMap = Object.fromEntries(peers.map((p) => [p.id, p]));
  const agentMap = Object.fromEntries(agents.map((a) => [a.id, a]));

  if (isLoading) return <p className={css({ color: "#4a4a52" })}>読み込み中...</p>;

  return (
    <>
      <PageHead
        title="内線アカウント"
        subtitle="電話番号とAIエージェントを管理します"
        actions={
          <Link to="/extensions/new" className={btnPrimary}>
            追加
          </Link>
        }
      />

      <DataTable
        columns={[
          {
            header: "番号",
            accessor: (ext) => <strong>{ext.number}</strong>,
          },
          {
            header: "名前",
            accessor: (ext) => ext.display_name,
          },
          {
            header: "種別",
            accessor: (ext) => {
              if (ext.type === "ai_agent") return <Tag variant="info">AI</Tag>;
              if (ext.type === "ivr") return <Tag variant="info">IVR</Tag>;
              if (ext.type === "ai_workflow") return <Tag variant="info">AI Workflow</Tag>;
              return <Tag variant="muted">電話</Tag>;
            },
          },
          {
            header: "状態",
            accessor: (ext) =>
              ext.enabled ? <Tag variant="ok">有効</Tag> : <Tag variant="ng">無効</Tag>,
          },
          {
            header: "接続先",
            accessor: (ext) => {
              if (ext.type === "phone" && ext.peer_id && peerMap[ext.peer_id]) {
                return <Tag variant="info">{peerMap[ext.peer_id].username}</Tag>;
              }
              if (ext.type === "ai_agent" && ext.ai_agent_id && agentMap[ext.ai_agent_id]) {
                const a = agentMap[ext.ai_agent_id];
                return (
                  <Tag variant="muted">
                    {a.llm_provider}/{a.llm_model}
                  </Tag>
                );
              }
              return "-";
            },
          },
          {
            header: "",
            className: css({ textAlign: "right", whiteSpace: "nowrap" }),
            accessor: (ext) => {
              const isWorkflow = ext.type === "ivr" || ext.type === "ai_workflow";
              return (
                <div className={css({ display: "flex", justifyContent: "flex-end", gap: "4px" })}>
                  {isWorkflow ? (
                    <Link to="/workflows" className={btnEdit}>
                      ワークフロー
                    </Link>
                  ) : (
                    <>
                      <Link
                        to="/extensions/$extensionId/edit"
                        params={{ extensionId: String(ext.id) }}
                        className={btnEdit}
                      >
                        編集
                      </Link>
                      <button
                        type="button"
                        onClick={() => {
                          const msg =
                            ext.type === "ai_agent"
                              ? `内線番号 ${ext.number} を削除しますか？（AIエージェント設定も削除されます）`
                              : `内線番号 ${ext.number} を削除しますか？`;
                          if (confirm(msg)) deleteMutation.mutate(ext.id);
                        }}
                        className={btnDelete}
                      >
                        削除
                      </button>
                    </>
                  )}
                </div>
              );
            },
          },
        ]}
        data={extensions}
        emptyMessage="内線アカウントがまだありません"
        emptyAction={
          <Link to="/extensions/new" className={btnPrimary}>
            追加する
          </Link>
        }
      />
    </>
  );
}
