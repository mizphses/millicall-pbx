import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createFileRoute, Link, redirect } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { css } from "../../styled-system/css";
import { inputClass } from "../components/FormCard";
import { PageHead } from "../components/PageHead";
import { api } from "../lib/api";

export const Route = createFileRoute("/settings")({
  beforeLoad: ({ context }) => {
    if (!context.auth.isAuthenticated) throw redirect({ to: "/login" });
  },
  component: SettingsPage,
});

interface SettingItem {
  key: string;
  value: string;
  description: string | null;
}

function SettingsPage() {
  const queryClient = useQueryClient();

  const { data: settings, isLoading } = useQuery({
    queryKey: ["settings"],
    queryFn: () => api.get<SettingItem[]>("/settings"),
  });

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

  const mutation = useMutation({
    mutationFn: (items: { key: string; value: string }[]) =>
      api.put("/settings", items.filter((e) => e.key.trim())),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["settings"] });
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
    mutation.mutate(entries);
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
        <h2 className={css({ fontSize: "15px", fontWeight: 600, marginBottom: "12px" })}>
          設定値
        </h2>

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
    </>
  );
}
