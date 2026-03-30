import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createFileRoute, Link, redirect } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { css } from "../../styled-system/css";
import { inputClass } from "../components/FormCard";
import { PageHead } from "../components/PageHead";
import { $api } from "../lib/client";

export const Route = createFileRoute("/settings")({
  beforeLoad: ({ context }) => {
    if (!context.auth.isAuthenticated) throw redirect({ to: "/login" });
  },
  component: SettingsPage,
});

function SettingsPage() {
  const queryClient = useQueryClient();

  const { data: settings, isLoading } = $api.useQuery("get", "/api/settings");

  const [entries, setEntries] = useState<{ key: string; value: string }[]>([]);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (settings && Array.isArray(settings)) {
      const arr = settings.map((item) => ({
        key: item.key,
        value: item.value,
      }));
      if (arr.length === 0) {
        arr.push({ key: "", value: "" });
      }
      setEntries(arr);
    }
  }, [settings]);

  const mutation = $api.useMutation("put", "/api/settings", {
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["get", "/api/settings"] });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    },
  });

  if (isLoading) return <p className={css({ color: "#4a4a52" })}>読み込み中...</p>;

  function updateEntry(index: number, field: "key" | "value", val: string) {
    setEntries((prev) => prev.map((e, i) => (i === index ? { ...e, [field]: val } : e)));
  }

  function addEntry() {
    setEntries((prev) => [...prev, { key: "", value: "" }]);
  }

  function removeEntry(index: number) {
    setEntries((prev) => prev.filter((_, i) => i !== index));
  }

  function handleSave() {
    mutation.mutate({
      body: entries.filter((e) => e.key.trim()),
    });
  }

  return (
    <>
      <PageHead title="詳細設定" subtitle="APIキーやシステム設定を管理します" />

      <div
        className={css({
          background: "#ffffff",
          border: "1px solid #d4d2cd",
          borderRadius: "6px",
          padding: "20px",
          marginBottom: "20px",
        })}
      >
        <h2 className={css({ fontSize: "15px", fontWeight: 600, marginBottom: "12px" })}>設定値</h2>

        <div className={css({ display: "flex", flexDirection: "column", gap: "8px" })}>
          {entries.map((entry, i) => (
            <div
              key={`setting-${i}`}
              className={css({ display: "flex", gap: "8px", alignItems: "flex-start" })}
            >
              <input
                type="text"
                className={`${inputClass} ${css({ flex: "1" })}`}
                value={entry.key}
                onChange={(e) => updateEntry(i, "key", e.target.value)}
                placeholder="キー（例: google_api_key）"
              />
              <input
                type="password"
                className={`${inputClass} ${css({ flex: "2" })}`}
                value={entry.value}
                onChange={(e) => updateEntry(i, "value", e.target.value)}
                placeholder="値"
              />
              <button
                type="button"
                onClick={() => removeEntry(i)}
                className={css({
                  display: "inline-flex",
                  alignItems: "center",
                  padding: "10px",
                  fontSize: "13px",
                  color: "#b83232",
                  border: "1px solid #d4d2cd",
                  borderRadius: "5px",
                  background: "transparent",
                  cursor: "pointer",
                  minHeight: "38px",
                  _hover: { background: "#fce8e8", borderColor: "#b83232" },
                })}
              >
                &times;
              </button>
            </div>
          ))}
        </div>

        <div className={css({ display: "flex", gap: "8px", marginTop: "16px" })}>
          <button
            type="button"
            onClick={addEntry}
            className={css({
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              padding: "7px 14px",
              fontSize: "13px",
              fontWeight: 500,
              borderRadius: "5px",
              background: "#ffffff",
              color: "#1b1b1f",
              border: "1px solid #d4d2cd",
              cursor: "pointer",
              _hover: { background: "#e6e4e0" },
            })}
          >
            + 追加
          </button>
        </div>

        <div
          className={css({
            display: "flex",
            alignItems: "center",
            gap: "12px",
            marginTop: "24px",
            paddingTop: "16px",
            borderTop: "1px solid #e6e4e0",
          })}
        >
          <button
            type="button"
            onClick={handleSave}
            disabled={mutation.isPending}
            className={css({
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              padding: "9px 18px",
              fontSize: "14px",
              fontWeight: 500,
              borderRadius: "5px",
              background: "#c45d2c",
              color: "#ffffff",
              border: "none",
              cursor: "pointer",
              _hover: { background: "#a84e24" },
              _disabled: { opacity: 0.5 },
            })}
          >
            {mutation.isPending ? "保存中..." : "保存"}
          </button>
          {saved && (
            <span className={css({ fontSize: "13px", color: "#2a7e4f" })}>保存しました</span>
          )}
        </div>
      </div>

      <div
        className={css({
          background: "#ffffff",
          border: "1px solid #d4d2cd",
          borderRadius: "6px",
          padding: "20px",
        })}
      >
        <h2 className={css({ fontSize: "15px", fontWeight: 600, marginBottom: "8px" })}>
          トランク設定
        </h2>
        <p className={css({ fontSize: "13px", color: "#4a4a52", marginBottom: "12px" })}>
          外線トランクの設定は専用ページで行います。
        </p>
        <Link
          to="/trunks"
          className={css({
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "7px 14px",
            fontSize: "13px",
            fontWeight: 500,
            borderRadius: "5px",
            background: "#ffffff",
            color: "#1b1b1f",
            border: "1px solid #d4d2cd",
            textDecoration: "none",
            _hover: { background: "#e6e4e0" },
          })}
        >
          外線トランク管理へ
        </Link>
      </div>

      <div
        className={css({
          background: "#ffffff",
          border: "1px solid #d4d2cd",
          borderRadius: "6px",
          padding: "20px",
          marginTop: "20px",
        })}
      >
        <h2 className={css({ fontSize: "15px", fontWeight: 600, marginBottom: "8px" })}>MCP連携</h2>
        <p className={css({ fontSize: "13px", color: "#4a4a52", marginBottom: "12px" })}>
          Claude DesktopなどのAIアシスタントからMillicallを操作するためのMCP設定ガイドです。
        </p>
        <Link
          to="/mcp-guide"
          className={css({
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "7px 14px",
            fontSize: "13px",
            fontWeight: 500,
            borderRadius: "5px",
            background: "#ffffff",
            color: "#1b1b1f",
            border: "1px solid #d4d2cd",
            textDecoration: "none",
            _hover: { background: "#e6e4e0" },
          })}
        >
          MCP連携ガイドを見る
        </Link>
      </div>

      <WireGuardSection />
    </>
  );
}

function WireGuardSection() {
  const { data: wg, isLoading } = useQuery({
    queryKey: ["wireguard"],
    queryFn: async () => {
      const token = localStorage.getItem("millicall_token");
      const res = await fetch("/api/wireguard", {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!res.ok) return { active: false, error: "Failed to fetch" };
      return (await res.json()) as {
        active: boolean;
        server_public_key?: string;
        listen_port?: number;
        address?: string;
        peers?: { public_key: string; endpoint?: string; allowed_ips: string; latest_handshake?: number; transfer_rx: number; transfer_tx: number }[];
        error?: string;
      };
    },
  });

  const [copied, setCopied] = useState(false);

  if (isLoading) return null;

  const cardStyle = css({
    background: "#ffffff",
    border: "1px solid #d4d2cd",
    borderRadius: "6px",
    padding: "20px",
    marginTop: "20px",
  });

  if (!wg?.active) {
    return (
      <div className={cardStyle}>
        <h2 className={css({ fontSize: "15px", fontWeight: 600, marginBottom: "8px" })}>
          VPN (WireGuard)
        </h2>
        <p className={css({ fontSize: "13px", color: "#4a4a52" })}>
          WireGuardが起動していません
        </p>
      </div>
    );
  }

  const clientConfig = `[Interface]
PrivateKey = <YOUR_PRIVATE_KEY>
Address = 10.100.0.2/24

[Peer]
PublicKey = ${wg.server_public_key}
Endpoint = <SERVER_ADDRESS>:${wg.listen_port}
AllowedIPs = 10.100.0.0/24, 172.20.0.0/16
PersistentKeepalive = 25`;

  function handleCopy() {
    navigator.clipboard.writeText(clientConfig);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  function formatBytes(bytes: number) {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  return (
    <div className={cardStyle}>
      <h2 className={css({ fontSize: "15px", fontWeight: 600, marginBottom: "12px" })}>
        VPN (WireGuard)
      </h2>

      <div className={css({ display: "flex", gap: "16px", flexWrap: "wrap", marginBottom: "16px" })}>
        <div>
          <span className={css({ fontSize: "12px", color: "#4a4a52" })}>ステータス</span>
          <div className={css({ fontSize: "13px", fontWeight: 500, color: "#2a7e4f" })}>稼働中</div>
        </div>
        <div>
          <span className={css({ fontSize: "12px", color: "#4a4a52" })}>ポート</span>
          <div className={css({ fontSize: "13px", fontWeight: 500 })}>{wg.listen_port}/UDP</div>
        </div>
        <div>
          <span className={css({ fontSize: "12px", color: "#4a4a52" })}>接続数</span>
          <div className={css({ fontSize: "13px", fontWeight: 500 })}>
            {wg.peers?.filter((p) => p.latest_handshake).length ?? 0} / {wg.peers?.length ?? 0}
          </div>
        </div>
      </div>

      {wg.peers && wg.peers.length > 0 && (
        <div className={css({ marginBottom: "16px" })}>
          <h3 className={css({ fontSize: "13px", fontWeight: 600, marginBottom: "8px" })}>ピア</h3>
          {wg.peers.map((peer) => (
            <div
              key={peer.public_key}
              className={css({
                fontSize: "12px",
                padding: "8px 10px",
                background: "#f8f7f5",
                borderRadius: "4px",
                marginBottom: "4px",
                display: "flex",
                gap: "16px",
                flexWrap: "wrap",
              })}
            >
              <span className={css({ fontFamily: "monospace" })}>{peer.public_key.slice(0, 16)}...</span>
              <span className={css({ color: peer.latest_handshake ? "#2a7e4f" : "#8e8e96" })}>
                {peer.latest_handshake
                  ? `接続中 (${formatBytes(peer.transfer_rx)} / ${formatBytes(peer.transfer_tx)})`
                  : "未接続"}
              </span>
            </div>
          ))}
        </div>
      )}

      <h3 className={css({ fontSize: "13px", fontWeight: 600, marginBottom: "8px" })}>
        クライアント設定
      </h3>
      <p className={css({ fontSize: "12px", color: "#4a4a52", marginBottom: "8px" })}>
        &lt;YOUR_PRIVATE_KEY&gt; と &lt;SERVER_ADDRESS&gt; を置き換えてください
      </p>
      <pre
        className={css({
          background: "#1b1b1f",
          color: "#e0e0e0",
          padding: "14px",
          borderRadius: "5px",
          fontSize: "12px",
          lineHeight: "1.6",
          overflow: "auto",
          fontFamily: "monospace",
        })}
      >
        {clientConfig}
      </pre>
      <button
        type="button"
        onClick={handleCopy}
        className={css({
          marginTop: "8px",
          display: "inline-flex",
          alignItems: "center",
          justifyContent: "center",
          padding: "7px 14px",
          fontSize: "13px",
          fontWeight: 500,
          borderRadius: "5px",
          background: "#ffffff",
          color: "#1b1b1f",
          border: "1px solid #d4d2cd",
          cursor: "pointer",
          _hover: { background: "#e6e4e0" },
        })}
      >
        {copied ? "コピーしました" : "コピー"}
      </button>
    </div>
  );
}
