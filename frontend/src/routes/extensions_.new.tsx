import { useQueryClient } from "@tanstack/react-query";
import { createFileRoute, redirect, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { css } from "../../styled-system/css";
import {
  FormCard,
  FormGroup,
  FormRow,
  FormSection,
  inputClass,
  selectClass,
} from "../components/FormCard";
import { PageHead } from "../components/PageHead";
import { $api } from "../lib/client";

export const Route = createFileRoute("/extensions_/new")({
  beforeLoad: ({ context }) => {
    if (!context.auth.isAuthenticated) throw redirect({ to: "/login" });
  },
  component: ExtensionNewPage,
});

const checkboxLabel = css({
  display: "inline-flex",
  alignItems: "center",
  gap: "8px",
  fontSize: "14px",
  cursor: "pointer",
  paddingBlock: "4px",
});

const checkboxInput = css({
  width: "16px",
  height: "16px",
  accentColor: "#c45d2c",
});

function ExtensionNewPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [number, setNumber] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [peerId, setPeerId] = useState("");
  const [enabled, setEnabled] = useState(true);

  const { data: peers } = $api.useQuery("get", "/api/peers");

  const mutation = $api.useMutation("post", "/api/extensions", {
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["extensions"] });
      navigate({ to: "/extensions" });
    },
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    mutation.mutate({
      body: {
        type: "phone",
        number,
        display_name: displayName,
        peer_id: peerId ? parseInt(peerId, 10) : null,
        enabled,
      },
    });
  }

  return (
    <>
      <PageHead title="内線アカウントを追加" />
      <FormCard
        onSubmit={handleSubmit}
        submitLabel="作成"
        cancelHref="/extensions"
        isSubmitting={mutation.isPending}
      >
        <FormSection title="基本情報" />
        <FormRow>
          <FormGroup label="内線番号">
            <input
              type="text"
              className={inputClass}
              value={number}
              onChange={(e) => setNumber(e.target.value)}
              placeholder="1001"
              required
              pattern="\d+"
            />
          </FormGroup>
          <FormGroup label="表示名">
            <input
              type="text"
              className={inputClass}
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="受付"
              required
            />
          </FormGroup>
        </FormRow>

        <FormSection title="接続先SIPピア" />
        <FormGroup label="SIPピア" hint="この内線番号にかかってきたときに鳴らすSIP電話機">
          <select
            className={selectClass}
            value={peerId}
            onChange={(e) => setPeerId(e.target.value)}
          >
            <option value="">-- 未割当 --</option>
            {(peers ?? []).map((p) => (
              <option key={p.id} value={p.id}>
                {p.username}
              </option>
            ))}
          </select>
        </FormGroup>

        <label className={checkboxLabel}>
          <input
            type="checkbox"
            className={checkboxInput}
            checked={enabled}
            onChange={(e) => setEnabled(e.target.checked)}
          />
          この内線を有効にする
        </label>
      </FormCard>
    </>
  );
}
