import { useMutation, useQueryClient } from "@tanstack/react-query";
import { createFileRoute, redirect, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import {
  FormCard,
  FormGroup,
  FormRow,
  FormSection,
  inputClass,
  textareaClass,
} from "../components/FormCard";
import { PageHead } from "../components/PageHead";
import { api } from "../lib/api";

export const Route = createFileRoute("/contacts_/new")({
  beforeLoad: ({ context }) => {
    if (!context.auth.isAuthenticated) throw redirect({ to: "/login" });
  },
  component: ContactNewPage,
});

function ContactNewPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [phoneNumber, setPhoneNumber] = useState("");
  const [company, setCompany] = useState("");
  const [department, setDepartment] = useState("");
  const [notes, setNotes] = useState("");

  const mutation = useMutation({
    mutationFn: (body: Record<string, unknown>) => api.post("/contacts", body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["contacts"] });
      navigate({ to: "/contacts" });
    },
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    mutation.mutate({
      name,
      phone_number: phoneNumber,
      company: company || null,
      department: department || null,
      notes: notes || null,
    });
  }

  return (
    <>
      <PageHead title="連絡先を追加" />
      <FormCard
        onSubmit={handleSubmit}
        submitLabel="作成"
        cancelHref="/contacts"
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
              placeholder="山田太郎"
              required
            />
          </FormGroup>
          <FormGroup label="電話番号">
            <input
              type="text"
              className={inputClass}
              value={phoneNumber}
              onChange={(e) => setPhoneNumber(e.target.value)}
              placeholder="03-1234-5678"
              required
            />
          </FormGroup>
        </FormRow>

        <FormSection title="所属" />
        <FormRow>
          <FormGroup label="会社">
            <input
              type="text"
              className={inputClass}
              value={company}
              onChange={(e) => setCompany(e.target.value)}
              placeholder="株式会社サンプル"
            />
          </FormGroup>
          <FormGroup label="部署">
            <input
              type="text"
              className={inputClass}
              value={department}
              onChange={(e) => setDepartment(e.target.value)}
              placeholder="営業部"
            />
          </FormGroup>
        </FormRow>

        <FormSection title="その他" />
        <FormGroup label="メモ">
          <textarea
            className={textareaClass}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="メモを入力..."
            rows={4}
          />
        </FormGroup>
      </FormCard>
    </>
  );
}
