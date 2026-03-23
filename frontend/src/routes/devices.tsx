import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createFileRoute, redirect } from "@tanstack/react-router";
import { useState } from "react";
import { css } from "../../styled-system/css";
import { DataTable } from "../components/DataTable";
import { Modal } from "../components/Modal";
import { PageHead } from "../components/PageHead";
import { Tag } from "../components/Tag";
import { api } from "../lib/api";

export const Route = createFileRoute("/devices")({
  beforeLoad: ({ context }) => {
    if (!context.auth.isAuthenticated) throw redirect({ to: "/login" });
  },
  component: DevicesPage,
});

interface Device {
  id: number;
  mac_address: string;
  ip_address: string | null;
  hostname: string | null;
  model: string | null;
  peer_id: number | null;
  extension_id: number | null;
  provisioned: boolean;
  last_seen: string | null;
}

interface Extension {
  id: number;
  number: string;
  display_name: string;
  type: string;
  peer_id: number | null;
}

const codeStyle = css({
  fontFamily: "'JetBrains Mono', monospace",
  fontSize: "12px",
  background: "#e6e4e0",
  paddingInline: "6px",
  paddingBlock: "2px",
  borderRadius: "3px",
});

const inputStyle = css({
  width: "100%",
  padding: "8px 10px",
  fontSize: "14px",
  color: "#1b1b1f",
  background: "#ffffff",
  border: "1px solid #d4d2cd",
  borderRadius: "5px",
  outline: "none",
  minHeight: "38px",
});

const btnPrimary = css({
  padding: "7px 14px",
  fontSize: "13px",
  fontWeight: 500,
  borderRadius: "5px",
  background: "#c45d2c",
  color: "#ffffff",
  border: "none",
  cursor: "pointer",
  _hover: { background: "#a84e24" },
  _disabled: { opacity: 0.5 },
});

const btnSecondary = css({
  padding: "7px 14px",
  fontSize: "13px",
  fontWeight: 500,
  borderRadius: "5px",
  background: "#ffffff",
  color: "#1b1b1f",
  border: "1px solid #d4d2cd",
  cursor: "pointer",
  _hover: { background: "#e6e4e0" },
});

const tabBtn = (active: boolean) =>
  css({
    padding: "6px 14px",
    fontSize: "13px",
    fontWeight: 500,
    borderRadius: "5px",
    cursor: "pointer",
    background: active ? "#c45d2c" : "#ffffff",
    color: active ? "#ffffff" : "#1b1b1f",
    border: active ? "none" : "1px solid #d4d2cd",
  });

function DevicesPage() {
  const queryClient = useQueryClient();
  const [provisionTarget, setProvisionTarget] = useState<Device | null>(null);
  const [mode, setMode] = useState<"assign" | "create">("create");
  const [selectedExtId, setSelectedExtId] = useState("");
  const [newNumber, setNewNumber] = useState("");
  const [newName, setNewName] = useState("");
  const [result, setResult] = useState<{
    sip_username: string;
    sip_password: string;
  } | null>(null);

  const { data: devices = [], isLoading } = useQuery({
    queryKey: ["devices"],
    queryFn: () => api.get<Device[]>("/devices"),
  });

  const { data: extensions = [] } = useQuery({
    queryKey: ["extensions"],
    queryFn: () => api.get<Extension[]>("/extensions"),
  });

  const phoneExtensions = extensions.filter((e) => e.type === "phone" && e.peer_id != null);

  const scanMutation = useMutation({
    mutationFn: () => api.post("/devices/scan"),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["devices"] }),
  });

  const assignMutation = useMutation({
    mutationFn: ({ deviceId, extensionId }: { deviceId: number; extensionId: number }) =>
      api.post(`/devices/${deviceId}/assign-extension`, { extension_id: extensionId }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["devices"] });
      closeModal();
    },
  });

  const quickProvisionMutation = useMutation({
    mutationFn: ({
      deviceId,
      extension_number,
      display_name,
    }: {
      deviceId: number;
      extension_number: string;
      display_name: string;
    }) =>
      api.post<{ sip_username: string; sip_password: string }>(
        `/devices/${deviceId}/quick-provision`,
        { extension_number, display_name },
      ),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["devices"] });
      queryClient.invalidateQueries({ queryKey: ["extensions"] });
      queryClient.invalidateQueries({ queryKey: ["peers"] });
      setResult(data);
    },
  });

  function closeModal() {
    setProvisionTarget(null);
    setSelectedExtId("");
    setNewNumber("");
    setNewName("");
    setResult(null);
  }

  function handleSubmit() {
    if (!provisionTarget) return;
    if (mode === "assign" && selectedExtId) {
      assignMutation.mutate({
        deviceId: provisionTarget.id,
        extensionId: Number(selectedExtId),
      });
    } else if (mode === "create" && newNumber) {
      quickProvisionMutation.mutate({
        deviceId: provisionTarget.id,
        extension_number: newNumber,
        display_name: newName || newNumber,
      });
    }
  }

  const isPending = assignMutation.isPending || quickProvisionMutation.isPending;

  if (isLoading) return <p className={css({ color: "#4a4a52" })}>読み込み中...</p>;

  return (
    <>
      <PageHead
        title="デバイス管理"
        subtitle="ネットワーク上のSIP電話機を検出・プロビジョニングします"
        actions={
          <button
            type="button"
            onClick={() => scanMutation.mutate()}
            disabled={scanMutation.isPending}
            className={btnPrimary}
          >
            {scanMutation.isPending ? "スキャン中..." : "ネットワークスキャン"}
          </button>
        }
      />

      <DataTable
        columns={[
          {
            header: "MACアドレス",
            accessor: (d) => <code className={codeStyle}>{d.mac_address}</code>,
          },
          { header: "IPアドレス", accessor: (d) => d.ip_address || "-" },
          { header: "ホスト名", accessor: (d) => d.hostname || "-" },
          {
            header: "最終検出",
            accessor: (d) => {
              if (!d.last_seen) return "-";
              const date = new Date(d.last_seen);
              return date.toLocaleString("ja-JP", {
                month: "numeric",
                day: "numeric",
                hour: "2-digit",
                minute: "2-digit",
              });
            },
          },
          {
            header: "状態",
            accessor: (d) =>
              d.provisioned ? <Tag variant="ok">設定済み</Tag> : <Tag variant="ng">未設定</Tag>,
          },
          {
            header: "",
            className: css({ textAlign: "right", whiteSpace: "nowrap" }),
            accessor: (d) => (
              <button
                type="button"
                onClick={() => {
                  setProvisionTarget(d);
                  setResult(null);
                  setMode("create");
                }}
                className={btnSecondary}
              >
                プロビジョニング
              </button>
            ),
          },
        ]}
        data={devices}
        emptyMessage="デバイスが検出されていません。スキャンを実行してください。"
      />

      <Modal open={!!provisionTarget} title="プロビジョニング" onClose={closeModal}>
        <p className={css({ fontSize: "13px", color: "#4a4a52", marginBottom: "12px" })}>
          デバイス <code className={codeStyle}>{provisionTarget?.mac_address}</code>
        </p>

        {result ? (
          <div>
            <div
              className={css({
                background: "#e3f4eb",
                border: "1px solid #2a7e4f",
                borderRadius: "5px",
                padding: "16px",
                marginBottom: "16px",
              })}
            >
              <p
                className={css({
                  fontSize: "13px",
                  fontWeight: 600,
                  color: "#2a7e4f",
                  marginBottom: "8px",
                })}
              >
                プロビジョニング完了
              </p>
              <p className={css({ fontSize: "13px", marginBottom: "4px" })}>
                SIPユーザー名: <code className={codeStyle}>{result.sip_username}</code>
              </p>
              <p className={css({ fontSize: "13px" })}>
                SIPパスワード: <code className={codeStyle}>{result.sip_password}</code>
              </p>
            </div>
            <p className={css({ fontSize: "12px", color: "#8e8e96", marginBottom: "16px" })}>
              電話機を再起動すると自動的に設定が反映されます。
            </p>
            <div className={css({ display: "flex", justifyContent: "flex-end" })}>
              <button type="button" onClick={closeModal} className={btnPrimary}>
                閉じる
              </button>
            </div>
          </div>
        ) : (
          <>
            <div className={css({ display: "flex", gap: "8px", marginBottom: "16px" })}>
              <button
                type="button"
                onClick={() => setMode("create")}
                className={tabBtn(mode === "create")}
              >
                新規作成
              </button>
              <button
                type="button"
                onClick={() => setMode("assign")}
                className={tabBtn(mode === "assign")}
              >
                既存の内線を割当
              </button>
            </div>

            {mode === "create" ? (
              <div className={css({ display: "flex", flexDirection: "column", gap: "12px" })}>
                <div>
                  <label
                    className={css({
                      display: "block",
                      fontSize: "13px",
                      fontWeight: 500,
                      marginBottom: "4px",
                    })}
                  >
                    内線番号
                  </label>
                  <input
                    type="text"
                    className={inputStyle}
                    value={newNumber}
                    onChange={(e) => setNewNumber(e.target.value)}
                    placeholder="4001"
                    pattern="\d+"
                    required
                  />
                  <div className={css({ fontSize: "12px", color: "#8e8e96", marginTop: "4px" })}>
                    SIPアカウントとパスワードは自動生成されます
                  </div>
                </div>
                <div>
                  <label
                    className={css({
                      display: "block",
                      fontSize: "13px",
                      fontWeight: 500,
                      marginBottom: "4px",
                    })}
                  >
                    表示名
                  </label>
                  <input
                    type="text"
                    className={inputStyle}
                    value={newName}
                    onChange={(e) => setNewName(e.target.value)}
                    placeholder="受付電話"
                  />
                </div>
              </div>
            ) : (
              <div>
                {phoneExtensions.length === 0 ? (
                  <p className={css({ fontSize: "13px", color: "#b83232" })}>
                    割当可能な電話タイプの内線がありません。
                  </p>
                ) : (
                  <>
                    <label
                      className={css({
                        display: "block",
                        fontSize: "13px",
                        fontWeight: 500,
                        marginBottom: "4px",
                      })}
                    >
                      内線を選択
                    </label>
                    <select
                      value={selectedExtId}
                      onChange={(e) => setSelectedExtId(e.target.value)}
                      className={inputStyle}
                    >
                      <option value="">-- 選択 --</option>
                      {phoneExtensions.map((ext) => (
                        <option key={ext.id} value={ext.id}>
                          {ext.number} - {ext.display_name}
                        </option>
                      ))}
                    </select>
                  </>
                )}
              </div>
            )}

            <div
              className={css({
                display: "flex",
                gap: "8px",
                justifyContent: "flex-end",
                marginTop: "20px",
              })}
            >
              <button type="button" onClick={closeModal} className={btnSecondary}>
                キャンセル
              </button>
              <button
                type="button"
                onClick={handleSubmit}
                disabled={
                  isPending ||
                  (mode === "assign" && !selectedExtId) ||
                  (mode === "create" && !newNumber)
                }
                className={btnPrimary}
              >
                {isPending ? "処理中..." : mode === "create" ? "作成して適用" : "適用"}
              </button>
            </div>
          </>
        )}
      </Modal>
    </>
  );
}
