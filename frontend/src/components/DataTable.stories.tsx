import type { Meta, StoryObj } from "@storybook/react-vite";
import { css } from "../../styled-system/css";
import { DataTable } from "./DataTable";
import { Tag } from "./Tag";

interface SampleRow {
  id: number;
  name: string;
  number: string;
  enabled: boolean;
}

const meta: Meta<typeof DataTable<SampleRow>> = {
  title: "Components/DataTable",
  component: DataTable,
};
export default meta;

type Story = StoryObj<typeof DataTable<SampleRow>>;

const sampleData: SampleRow[] = [
  { id: 1, name: "受付", number: "1001", enabled: true },
  { id: 2, name: "営業部", number: "1002", enabled: true },
  { id: 3, name: "技術部", number: "1003", enabled: false },
  { id: 4, name: "受付AI", number: "9000", enabled: true },
];

const columns = [
  {
    header: "番号",
    accessor: (row: SampleRow) => <strong>{row.number}</strong>,
  },
  {
    header: "名前",
    accessor: (row: SampleRow) => row.name,
  },
  {
    header: "状態",
    accessor: (row: SampleRow) =>
      row.enabled ? <Tag variant="ok">有効</Tag> : <Tag variant="ng">無効</Tag>,
  },
  {
    header: "",
    className: css({ textAlign: "right" }),
    accessor: (_row: SampleRow) => (
      <button
        type="button"
        className={css({
          paddingInline: "10px",
          paddingBlock: "4px",
          fontSize: "12px",
          fontWeight: 500,
          borderRadius: "5px",
          background: "transparent",
          color: "#4a4a52",
          cursor: "pointer",
          _hover: { background: "#e6e4e0" },
        })}
      >
        編集
      </button>
    ),
  },
];

export const WithData: Story = {
  args: {
    columns,
    data: sampleData,
  },
};

export const Empty: Story = {
  args: {
    columns,
    data: [],
    emptyMessage: "内線アカウントがまだありません",
    emptyAction: (
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
        追加する
      </button>
    ),
  },
};
