import { useMutation, useQueryClient } from "@tanstack/react-query";
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
  textareaClass,
} from "../components/FormCard";
import { PageHead } from "../components/PageHead";
import { api } from "../lib/api";

export const Route = createFileRoute("/workflows_/new")({
  beforeLoad: ({ context }) => {
    if (!context.auth.isAuthenticated) throw redirect({ to: "/login" });
  },
  component: WorkflowNewPage,
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

function WorkflowNewPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [number, setNumber] = useState("");
  const [description, setDescription] = useState("");
  const [workflowType, setWorkflowType] = useState("ivr");
  const [enabled, setEnabled] = useState(true);
  const [ttsProvider, setTtsProvider] = useState("google");
  const [googleVoice, setGoogleVoice] = useState("ja-JP-Chirp3-HD-Aoede");
  const [coefontId, setCoefontId] = useState("");

  const mutation = useMutation({
    mutationFn: (body: Record<string, unknown>) => api.post<{ id: number }>("/workflows", body),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["workflows"] });
      navigate({
        to: "/workflows/$workflowId/edit",
        params: { workflowId: String(data.id) },
      });
    },
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    mutation.mutate({
      name,
      number,
      description,
      workflow_type: workflowType,
      default_tts_config: {
        tts_provider: ttsProvider,
        google_tts_voice: googleVoice,
        coefont_voice_id: coefontId,
      },
      enabled,
    });
  }

  return (
    <>
      <PageHead title="ワークフローを追加" />
      <FormCard
        onSubmit={handleSubmit}
        submitLabel="作成してエディタを開く"
        cancelHref="/workflows"
        isSubmitting={mutation.isPending}
      >
        <FormSection title="基本情報" />
        <FormRow>
          <FormGroup label="名前">
            <input
              type="text"
              className={inputClass}
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="営業時間IVR"
              required
            />
          </FormGroup>
          <FormGroup label="内線番号" hint="この番号にかけるとワークフローが実行されます">
            <input
              type="text"
              className={inputClass}
              value={number}
              onChange={(e) => setNumber(e.target.value)}
              placeholder="9000"
              required
              pattern="\d+"
            />
          </FormGroup>
        </FormRow>

        <FormGroup label="説明">
          <textarea
            className={textareaClass}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="このワークフローの説明を入力..."
            rows={3}
          />
        </FormGroup>

        <FormGroup label="ワークフロータイプ">
          <select
            className={selectClass}
            value={workflowType}
            onChange={(e) => setWorkflowType(e.target.value)}
            required
          >
            <option value="ivr">IVR</option>
            <option value="ai_workflow">AI Call Workflow</option>
          </select>
        </FormGroup>

        <FormSection title="デフォルトTTS設定" />
        <FormRow>
          <FormGroup label="TTSプロバイダ">
            <select
              className={selectClass}
              value={ttsProvider}
              onChange={(e) => setTtsProvider(e.target.value)}
            >
              <option value="google">Google Chirp3 HD</option>
              <option value="coefont">CoeFont</option>
            </select>
          </FormGroup>
          {ttsProvider === "google" ? (
            <FormGroup label="Google TTSボイス">
              <select
                className={selectClass}
                value={googleVoice}
                onChange={(e) => setGoogleVoice(e.target.value)}
              >
                <option value="ja-JP-Chirp3-HD-Aoede">Aoede（女性）</option>
                <option value="ja-JP-Chirp3-HD-Kore">Kore（女性）</option>
                <option value="ja-JP-Chirp3-HD-Leda">Leda（女性）</option>
                <option value="ja-JP-Chirp3-HD-Zephyr">Zephyr（女性）</option>
                <option value="ja-JP-Chirp3-HD-Charon">Charon（男性）</option>
                <option value="ja-JP-Chirp3-HD-Fenrir">Fenrir（男性）</option>
                <option value="ja-JP-Chirp3-HD-Orus">Orus（男性）</option>
                <option value="ja-JP-Chirp3-HD-Puck">Puck（男性）</option>
              </select>
            </FormGroup>
          ) : (
            <FormGroup label="CoeFont ボイスID">
              <input
                type="text"
                className={inputClass}
                value={coefontId}
                onChange={(e) => setCoefontId(e.target.value)}
                placeholder="ボイスID"
              />
            </FormGroup>
          )}
        </FormRow>

        <label className={checkboxLabel}>
          <input
            type="checkbox"
            className={checkboxInput}
            checked={enabled}
            onChange={(e) => setEnabled(e.target.checked)}
          />
          このワークフローを有効にする
        </label>
      </FormCard>
    </>
  );
}
