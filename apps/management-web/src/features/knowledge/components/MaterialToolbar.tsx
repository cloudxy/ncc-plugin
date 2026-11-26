import { DeleteOutlined } from "@ant-design/icons";
import { Button, Input, Segmented, Select, Space, Tag } from "antd";
import type { Json } from "../../../shared/api";
import type { CodexGroup } from "../../../shared/studioApi";

export function MaterialToolbar({
  groups,
  group,
  currentGroup,
  kind,
  groupCounts,
  countsLoaded,
  qInput,
  view,
  sortKey,
  canEdit,
  selectedCount,
  savedViews,
  onShowAll,
  onChooseGroup,
  onChooseKind,
  onQInputChange,
  onSearch,
  onViewChange,
  onSortChange,
  onSaveView,
  onRetireSelected,
  onApplyView,
}: {
  groups: CodexGroup[];
  group: string;
  currentGroup: CodexGroup | undefined;
  kind: string | undefined;
  groupCounts: { id: string; count: number }[] | undefined;
  countsLoaded: boolean;
  qInput: string;
  view: "表格" | "卡片";
  sortKey: string;
  canEdit: boolean;
  selectedCount: number;
  savedViews: [string, Json][];
  onShowAll: () => void;
  onChooseGroup: (id: string) => void;
  onChooseKind: (token: string) => void;
  onQInputChange: (next: string) => void;
  onSearch: (next: string) => void;
  onViewChange: (next: "表格" | "卡片") => void;
  onSortChange: (next: string) => void;
  onSaveView: () => void;
  onRetireSelected: () => void;
  onApplyView: (saved: Json) => void;
}) {
  return (
    <>
      <div className="mat-capsules" role="group" aria-label="万象设定领域">
        <Button
          type={group === "all" ? "primary" : "default"}
          aria-pressed={group === "all"}
          onClick={onShowAll}
        >
          全部
        </Button>
        {groups.map((item) => {
          const count = groupCounts?.find(
            (entry) => entry.id === item.id,
          )?.count;
          return (
            <Button
              key={item.id}
              type={group === item.id ? "primary" : "default"}
              aria-pressed={group === item.id}
              onClick={() => onChooseGroup(item.id)}
            >
              {item.label}
              {countsLoaded && typeof count === "number" ? ` ${count}` : ""}
            </Button>
          );
        })}
        <Button
          type={group === "other" ? "primary" : "default"}
          aria-pressed={group === "other"}
          onClick={() => onChooseGroup("other")}
        >
          其他/未归类
        </Button>
      </div>
      {currentGroup && (
        <Space wrap style={{ marginBottom: 12 }}>
          {currentGroup.kinds.map((token) => (
            <Tag.CheckableTag
              key={token}
              checked={kind === token}
              onChange={() => onChooseKind(token)}
            >
              {token}
            </Tag.CheckableTag>
          ))}
        </Space>
      )}
      <div className="table-toolbar">
        <Space wrap>
          <Input.Search
            aria-label="搜索作品资料"
            placeholder="搜索名称或原文，支持中文专名"
            value={qInput}
            allowClear
            style={{ width: 300 }}
            onChange={(event) => onQInputChange(event.target.value)}
            onSearch={(value) => onSearch(value)}
          />
          <Segmented
            aria-label="视图"
            value={view}
            options={["表格", "卡片"]}
            onChange={(value) => onViewChange(value as "表格" | "卡片")}
          />
          <Select
            aria-label="排序"
            value={sortKey}
            style={{ width: 140 }}
            options={[
              { value: "名称", label: "名称" },
              { value: "排序号", label: "排序号" },
              { value: "修订版本", label: "修订版本" },
            ]}
            onChange={(value) => onSortChange(value)}
          />
          <Button disabled={!canEdit} onClick={onSaveView}>
            保存视图
          </Button>
        </Space>
        <Space wrap>
          {selectedCount > 0 && <Tag>选中本页 {selectedCount} 项</Tag>}
          <Button
            danger
            icon={<DeleteOutlined />}
            disabled={!canEdit || selectedCount === 0}
            onClick={onRetireSelected}
          >
            批量停用
          </Button>
        </Space>
      </div>
      {savedViews.length > 0 && (
        <Space wrap style={{ marginBottom: 12 }}>
          {savedViews.map(([name, saved]) => (
            <Button key={name} onClick={() => onApplyView(saved)}>
              {name}
            </Button>
          ))}
        </Space>
      )}
    </>
  );
}
