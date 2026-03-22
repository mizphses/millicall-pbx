import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createFileRoute, redirect, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { css } from "../../styled-system/css";
import { FormCard, FormGroup, FormRow, FormSection, inputClass } from "../components/FormCard";
import { PageHead } from "../components/PageHead";
import { api } from "../lib/api";

export const Route = createFileRoute("/trunks_/$trunkId/edit")({
  beforeLoad: ({ context }) => {
    if (!context.auth.isAuthenticated) throw redirect({ to: "/login" });
  },
  component: TrunkEditPage,
});

interface Trunk {
  id: number;
  name: string;
  display_name: string;
  host: string;
  username: string;
  password: string;
  did_number: string;
  incoming_dest: string;
  outbound_prefixes: string;
  enabled: boolean;
}

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

function TrunkEditPage() {
  const { trunkId } = Route.useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data: trunk } = useQuery({
    queryKey: ["trunk", trunkId],
    queryFn: () => api.get<Trunk>(`/trunks/${trunkId}`),
  });

  const [name, setName] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [host, setHost] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [didNumber, setDidNumber] = useState("");
  const [incomingDest, setIncomingDest] = useState("");
  const [outboundPrefixes, setOutboundPrefixes] = useState("");
  const [enabled, setEnabled] = useState(true);

  useEffect(() => {
    if (trunk) {
      setName(trunk.name);
      setDisplayName(trunk.display_name);
      setHost(trunk.host);
      setUsername(trunk.username);
      setPassword(trunk.password);
      setDidNumber(trunk.did_number);
      setIncomingDest(trunk.incoming_dest);
      setOutboundPrefixes(trunk.outbound_prefixes);
      setEnabled(trunk.enabled);
    }
  }, [trunk]);

  const mutation = useMutation({
    mutationFn: (body: Record<string, unknown>) => api.put(`/trunks/${trunkId}`, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["trunks"] });
      queryClient.invalidateQueries({ queryKey: ["trunk", trunkId] });
      navigate({ to: "/trunks" });
    },
  });

  if (!trunk) return <p className={css({ color: "#4a4a52" })}>読み込み中...</p>;

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    mutation.mutate({
      name,
      display_name: displayName,
      host,
      username,
      password,
      did_number: didNumber,
      incoming_dest: incomingDest,
      outbound_prefixes: outboundPrefixes,
      enabled,
    });
  }

  return (
    <>
      <PageHead title="外線トランクを編集" />
      <FormCard
        onSubmit={handleSubmit}
        submitLabel="更新"
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
              required
            />
          </FormGroup>
          <FormGroup label="名前（slug）" hint="Asteriskのセクション名に使用">
            <input
              type="text"
              className={inputClass}
              value={name}
              onChange={(e) => setName(e.target.value)}
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
            />
          </FormGroup>
          <FormGroup label="着信先" hint="空欄で全内線に着信">
            <input
              type="text"
              className={inputClass}
              value={incomingDest}
              onChange={(e) => setIncomingDest(e.target.value)}
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
