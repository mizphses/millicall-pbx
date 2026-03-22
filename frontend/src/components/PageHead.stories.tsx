import type { Meta, StoryObj } from "@storybook/react-vite";
import { css } from "../../styled-system/css";
import { PageHead } from "./PageHead";

const meta: Meta<typeof PageHead> = {
  title: "Components/PageHead",
  component: PageHead,
};
export default meta;

type Story = StoryObj<typeof PageHead>;

export const Default: Story = {
  args: {
    title: "内線アカウント",
    subtitle: "電話番号とAIエージェントを管理します",
  },
};

export const WithActions: Story = {
  args: {
    title: "SIP電話機登録",
    subtitle: "SIPエンドポイントの認証アカウントを管理します",
    actions: (
      <button
        type="button"
        className={css({
          display: "inline-flex",
          alignItems: "center",
          justifyContent: "center",
          paddingInline: "14px",
          paddingBlock: "6px",
          fontSize: "13px",
          fontWeight: 500,
          borderRadius: "5px",
          background: "#c45d2c",
          color: "#ffffff",
          cursor: "pointer",
        })}
      >
        追加
      </button>
    ),
  },
};

export const TitleOnly: Story = {
  args: {
    title: "ダッシュボード",
  },
};
