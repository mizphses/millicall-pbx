import type { Meta, StoryObj } from "@storybook/react-vite";
import { useState } from "react";
import { css } from "../../styled-system/css";
import { Modal } from "./Modal";

const meta: Meta<typeof Modal> = {
  title: "Components/Modal",
  component: Modal,
};
export default meta;

type Story = StoryObj<typeof Modal>;

export const Default: Story = {
  args: {
    open: true,
    onClose: () => {},
    title: "確認ダイアログ",
    children: (
      <div className={css({ fontSize: "13px", color: "#4a4a52" })}>
        <p>この操作を実行してもよろしいですか？</p>
        <p className={css({ marginTop: "8px" })}>一度削除すると元に戻すことはできません。</p>
        <div
          className={css({
            display: "flex",
            gap: "8px",
            marginTop: "16px",
            justifyContent: "flex-end",
          })}
        >
          <button
            type="button"
            className={css({
              paddingInline: "14px",
              paddingBlock: "6px",
              fontSize: "13px",
              fontWeight: 500,
              borderRadius: "5px",
              background: "#ffffff",
              color: "#1b1b1f",
              border: "1px solid",
              borderColor: "#d4d2cd",
              cursor: "pointer",
            })}
          >
            キャンセル
          </button>
          <button
            type="button"
            className={css({
              paddingInline: "14px",
              paddingBlock: "6px",
              fontSize: "13px",
              fontWeight: 500,
              borderRadius: "5px",
              background: "#b83232",
              color: "#ffffff",
              cursor: "pointer",
            })}
          >
            削除する
          </button>
        </div>
      </div>
    ),
  },
};

function InteractiveModalDemo() {
  const [open, setOpen] = useState(false);
  return (
    <div>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className={css({
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
        モーダルを開く
      </button>
      <Modal open={open} onClose={() => setOpen(false)} title="ダイヤルガイド">
        <p className={css({ fontSize: "13px", color: "#4a4a52" })}>
          SIPフォンから外線発信するときのダイヤル方法一覧です。
        </p>
      </Modal>
    </div>
  );
}

export const Interactive: Story = {
  render: () => <InteractiveModalDemo />,
};
