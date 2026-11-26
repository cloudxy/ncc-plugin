import { SaveOutlined } from "@ant-design/icons";
import { Button, Select, Space, Tag } from "antd";
import {
  CHAPTER_STATUS_OPTIONS,
  chapterStatusLabel,
  type ChapterStatus,
} from "../../../shared/chapterStatus";
import type { StudioChapter } from "../../../shared/studioApi";

export function ChapterToolbarTitle({
  entityId,
  jobId,
  options,
  isNonChapterTarget,
  chapterStatus,
  phase,
  canEdit,
  dirty,
  hasBaseline,
  latestChapter,
  onChooseEntity,
  onStatusChange,
}: {
  entityId: string | undefined;
  jobId: string | undefined;
  options: { value: string; label: string; status?: string }[];
  isNonChapterTarget: boolean;
  chapterStatus: ChapterStatus;
  phase: "idle" | "save" | "start";
  canEdit: boolean;
  dirty: boolean;
  hasBaseline: boolean;
  latestChapter: StudioChapter | undefined;
  onChooseEntity: (value?: string) => void;
  onStatusChange: (nextStatus: ChapterStatus) => void;
}) {
  return (
    <Space wrap>
      <Select
        aria-label="编辑对象"
        allowClear
        placeholder="选择已有章节，或开始新稿"
        value={entityId}
        style={{ width: 196 }}
        showSearch
        optionFilterProp="label"
        options={options}
        optionRender={(option) => (
          <Space size={6}>
            <span>{option.data.label}</span>
            {option.data.status ? (
              <Tag style={{ marginInlineEnd: 0 }}>
                {chapterStatusLabel(String(option.data.status))}
              </Tag>
            ) : null}
          </Space>
        )}
        onChange={(value) => onChooseEntity(value)}
      />
      {!isNonChapterTarget && (
        <Select
          aria-label="章节状态"
          size="small"
          value={chapterStatus}
          disabled={phase !== "idle" || !canEdit}
          style={{ width: 92 }}
          options={CHAPTER_STATUS_OPTIONS}
          onChange={onStatusChange}
        />
      )}
      <Tag>{dirty ? "未保存修改" : hasBaseline ? "已保存修订" : "新稿"}</Tag>
      {!entityId && !jobId && latestChapter ? (
        <Button
          className="studio-resume-btn"
          size="small"
          type="link"
          onClick={() => onChooseEntity(latestChapter.id)}
        >
          {`继续最近章节：${latestChapter.name}`}
        </Button>
      ) : null}
    </Space>
  );
}

export function ChapterToolbarExtra({
  focus,
  canEdit,
  phase,
  onToggleFocus,
  onSave,
}: {
  focus: boolean;
  canEdit: boolean;
  phase: "idle" | "save" | "start";
  onToggleFocus: () => void;
  onSave: () => void;
}) {
  return (
    <Space wrap>
      <Button onClick={onToggleFocus}>{focus ? "退出专注" : "进入专注"}</Button>
      <Button
        disabled={!canEdit || phase !== "idle"}
        icon={<SaveOutlined />}
        onClick={onSave}
      >
        {phase === "save" ? "正在保存" : "保存修订"}
      </Button>
    </Space>
  );
}
