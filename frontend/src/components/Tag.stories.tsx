import type { Meta, StoryObj } from "@storybook/react-vite";
import { css } from "../../styled-system/css";
import { Tag } from "./Tag";

const meta: Meta<typeof Tag> = {
  title: "Components/Tag",
  component: Tag,
};
export default meta;

type Story = StoryObj<typeof Tag>;

export const Ok: Story = {
  args: {
    variant: "ok",
    children: "有効",
  },
};

export const Ng: Story = {
  args: {
    variant: "ng",
    children: "無効",
  },
};

export const Info: Story = {
  args: {
    variant: "info",
    children: "AI",
  },
};

export const Muted: Story = {
  args: {
    variant: "muted",
    children: "電話",
  },
};

export const Variants: Story = {
  render: () => (
    <div className={css({ display: "flex", gap: "8px", flexWrap: "wrap" })}>
      <Tag variant="ok">応答</Tag>
      <Tag variant="ng">不応答</Tag>
      <Tag variant="info">Google Gemini</Tag>
      <Tag variant="muted">UDP</Tag>
      <Tag variant="ok">設定済み</Tag>
      <Tag variant="ng">未設定</Tag>
      <Tag variant="muted">話中</Tag>
    </div>
  ),
};
