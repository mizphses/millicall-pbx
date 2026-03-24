import { useQueryClient } from "@tanstack/react-query";
import { createFileRoute, redirect, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { css } from "../../styled-system/css";
import { FormCard, FormGroup, FormRow, FormSection, inputClass } from "../components/FormCard";
import { PageHead } from "../components/PageHead";
import { $api } from "../lib/client";

export const Route = createFileRoute("/trunks_/new")({
  beforeLoad: ({ context }) => {
    if (!context.auth.isAuthenticated) throw redirect({ to: "/login" });
  },
  component: TrunkNewPage,
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

function TrunkNewPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [host, setHost] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [didNumber, setDidNumber] = useState("");
  const [incomingDest, setIncomingDest] = useState("");
  const [outboundPrefixes, setOutboundPrefixes] = useState("");
  const [enabled, setEnabled] = useState(true);

  const mutation = $api.useMutation("post", "/api/trunks", {
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["get", "/api/trunks"] });
      navigate({ to: "/trunks" });
    },
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    mutation.mutate({
      body: {
        name,
        display_name: displayName,
        host,
        username,
        password,
        did_number: didNumber,
        caller_id: "",
        incoming_dest: incomingDest,
        outbound_prefixes: outboundPrefixes,
        enabled,
      },
    });
  }

  return (
    <>
      <PageHead title="外線トランクを追加" />
      <FormCard
        onSubmit={handleSubmit}
        submitLabel="作成"
        cancelHref="/trunks"
        isSubmitting={mutation.isPending}
      >
        <FormSection title="基本情報" />
        <FormRow>
          <FormGroup label="表示名">
            <input
              type="text"
              className={inputClass}
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="ひかり電話"
              required
            />
          </FormGroup>
          <FormGroup label="名前（slug）" hint="Asteriskのセクション名に使用">
            <input
              type="text"
              className={inputClass}
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="hikari-trunk"
              required
            />
          </FormGroup>
        </FormRow>

        <FormSection title="SIPトランク接続" />
        <FormGroup label="ホスト">
          <input
            type="text"
            className={inputClass}
            value={host}
            onChange={(e) => setHost(e.target.value)}
            placeholder="sip.example.com"
            required
          />
        </FormGroup>
        <FormRow>
          <FormGroup label="ユーザー名">
            <input
              type="text"
              className={inputClass}
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="trunk-user"
              required
            />
          </FormGroup>
          <FormGroup label="パスワード">
            <input
              type="password"
              className={inputClass}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </FormGroup>
        </FormRow>

        <FormSection title="発着信設定" />
        <FormRow>
          <FormGroup label="電話番号（DID）">
            <input
              type="text"
              className={inputClass}
              value={didNumber}
              onChange={(e) => setDidNumber(e.target.value)}
              placeholder="0312345678"
            />
          </FormGroup>
          <FormGroup label="着信先" hint="空欄で全内線に着信">
            <input
              type="text"
              className={inputClass}
              value={incomingDest}
              onChange={(e) => setIncomingDest(e.target.value)}
              placeholder="1001"
            />
          </FormGroup>
        </FormRow>

        <FormGroup
          label="発信プレフィックス"
          hint="カンマ区切り。prepend付きは「prefix:prepend」（例: 9:,0:186）"
        >
          <input
            type="text"
            className={inputClass}
            value={outboundPrefixes}
            onChange={(e) => setOutboundPrefixes(e.target.value)}
            placeholder="9:, 186, 184"
          />
        </FormGroup>

        <label className={checkboxLabel}>
          <input
            type="checkbox"
            className={checkboxInput}
            checked={enabled}
            onChange={(e) => setEnabled(e.target.checked)}
          />
          このトランクを有効にする
        </label>
      </FormCard>
    </>
  );
}
