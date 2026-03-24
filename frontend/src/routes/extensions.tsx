import { createFileRoute, Link, redirect } from "@tanstack/react-router";
import { css } from "../../styled-system/css";
import { DataTable } from "../components/DataTable";
import { PageHead } from "../components/PageHead";
import { Tag } from "../components/Tag";
import { $api } from "../lib/client";

export const Route = createFileRoute("/extensions")({
  beforeLoad: ({ context }) => {
    if (!context.auth.isAuthenticated) throw redirect({ to: "/login" });
  },
  component: ExtensionsPage,
});

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
  cursor: "pointer",
  border: "none",
  _hover: { background: "#a84e24" },
});

const btnSub = css({
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
  border: "1px solid #d4d2cd",
  textDecoration: "none",
  cursor: "pointer",
  _hover: { background: "#e6e4e0" },
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
  border: "1px solid #d4d2cd",
  cursor: "pointer",
  _hover: { background: "#fce8e8", borderColor: "#b83232" },
});

function ExtensionsPage() {
  const { data: extensions, isLoading } = $api.useQuery("get", "/api/extensions");
  const { data: peers } = $api.useQuery("get", "/api/peers");
  const { data: workflows } = $api.useQuery("get", "/api/workflows");

  const deleteMutation = $api.useMutation("delete", "/api/extensions/{extension_id}", {
    onSuccess: () => {
      window.location.reload();
    },
  });

  const deleteWfMutation = $api.useMutation("delete", "/api/workflows/{workflow_id}", {
    onSuccess: () => {
      window.location.reload();
    },
  });

  const peerMap = Object.fromEntries((peers ?? []).map((p) => [p.id, p]));
  const wfByExtId = Object.fromEntries(
    (workflows ?? []).filter((w) => w.extension_id).map((w) => [w.extension_id!, w]),
  );

  if (isLoading) return <p className={css({ color: "#4a4a52" })}>読み込み中...</p>;

  return (
    <>
      <PageHead
        title="内線アカウント"
        subtitle="電話機・ワークフローを管理します"
        actions={
          <div className={css({ display: "flex", gap: "8px" })}>
            <Link to="/workflows/new" className={btnSub}>
              ワークフロー追加
            </Link>
            <Link to="/extensions/new" className={btnPrimary}>
              内線追加
            </Link>
          </div>
        }
      />

      <DataTable
        columns={[
          {
            header: "番号",
            sortValue: (ext) => ext.number,
            accessor: (ext) => (
              <strong
                className={css({ fontFamily: "'JetBrains Mono', monospace", fontSize: "13px" })}
              >
                {ext.number}
              </strong>
            ),
          },
          {
            header: "名前",
            sortValue: (ext) => ext.display_name,
            accessor: (ext) => ext.display_name,
          },
          {
            header: "種別",
            sortValue: (ext) => ext.type,
            accessor: (ext) => {
              if (ext.type === "workflow") return <Tag variant="ivr">ワークフロー</Tag>;
              return <Tag variant="phone">電話</Tag>;
            },
          },
          {
            header: "状態",
            sortValue: (ext) => (ext.enabled ? 0 : 1),
            accessor: (ext) =>
              ext.enabled ? <Tag variant="ok">有効</Tag> : <Tag variant="ng">無効</Tag>,
          },
          {
            header: "接続先",
            accessor: (ext) => {
              if (ext.type === "phone" && ext.peer_id && peerMap[ext.peer_id]) {
                return <Tag variant="phone">{peerMap[ext.peer_id].username}</Tag>;
              }
              const wf = wfByExtId[ext.id];
              if (wf) {
                return (
                  <Tag variant="ivr">
                    {wf.name} ({wf.node_count}ノード)
                  </Tag>
                );
              }
              return <span style={{ color: "#8e8e96" }}>-</span>;
            },
          },
          {
            header: "",
            className: css({ textAlign: "right", whiteSpace: "nowrap" }),
            accessor: (ext) => {
              const isWorkflow = ext.type === "workflow";
              const wf = wfByExtId[ext.id];
              return (
                <div className={css({ display: "flex", justifyContent: "flex-end", gap: "4px" })}>
                  {isWorkflow && wf ? (
                    <>
                      <Link
                        to="/workflows/$workflowId/edit"
                        params={{ workflowId: String(wf.id) }}
                        className={btnEdit}
                      >
                        エディタ
                      </Link>
                      <button
                        type="button"
                        onClick={() => {
                          if (
                            confirm(
                              `ワークフロー「${wf.name}」と内線 ${ext.number} を削除しますか？`,
                            )
                          )
                            deleteWfMutation.mutate({ params: { path: { workflow_id: wf.id } } });
                        }}
                        className={btnDelete}
                      >
                        削除
                      </button>
                    </>
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
                          if (confirm(`内線 ${ext.number} を削除しますか？`))
                            deleteMutation.mutate({ params: { path: { extension_id: ext.id } } });
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
        data={extensions ?? []}
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
