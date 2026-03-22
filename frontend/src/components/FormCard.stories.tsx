import type { Meta, StoryObj } from "@storybook/react-vite";
import { FormCard, FormGroup, FormRow, FormSection, inputClass, selectClass } from "./FormCard";

const meta: Meta<typeof FormCard> = {
  title: "Components/FormCard",
  component: FormCard,
};
export default meta;

type Story = StoryObj<typeof FormCard>;

export const Default: Story = {
  args: {
    onSubmit: (e) => e.preventDefault(),
    submitLabel: "保存",
    cancelHref: "#",
    isSubmitting: false,
    children: (
      <>
        <FormSection title="基本情報" />
        <FormRow>
          <FormGroup label="内線番号">
            <input type="text" className={inputClass} placeholder="1001" />
          </FormGroup>
          <FormGroup label="表示名">
            <input type="text" className={inputClass} placeholder="受付" />
          </FormGroup>
        </FormRow>
        <FormSection title="接続先" />
        <FormGroup label="SIPピア" hint="この内線番号にかかってきたときに鳴らすSIP電話機">
          <select className={selectClass}>
            <option value="">-- 未割当 --</option>
            <option value="1">phone01</option>
            <option value="2">phone02</option>
          </select>
        </FormGroup>
      </>
    ),
  },
};

export const Submitting: Story = {
  args: {
    onSubmit: (e) => e.preventDefault(),
    submitLabel: "作成",
    cancelHref: "#",
    isSubmitting: true,
    children: (
      <>
        <FormSection title="認証情報" />
        <FormRow>
          <FormGroup label="ユーザー名">
            <input type="text" className={inputClass} value="phone01" readOnly />
          </FormGroup>
          <FormGroup label="パスワード">
            <input type="password" className={inputClass} value="secret" readOnly />
          </FormGroup>
        </FormRow>
      </>
    ),
  },
};
