import { Collapse, Input, Switch } from "antd";
import {
  chapterStatusLabel,
  type ChapterStatus,
} from "../../../shared/chapterStatus";

export function BeatControlBar({
  beatOpen,
  onBeatOpenChange,
  chapterStatus,
  beatOutline,
  onBeatOutlineChange,
  hook,
  onHookChange,
  pov,
  onPovChange,
  plotline,
  onPlotlineChange,
  targetWords,
  onTargetWordsChange,
  targetCount,
  keyChapter,
  onKeyChapterChange,
  phase,
  canEdit,
}: {
  beatOpen: boolean;
  onBeatOpenChange: (open: boolean) => void;
  chapterStatus: ChapterStatus;
  beatOutline: string;
  onBeatOutlineChange: (value: string) => void;
  hook: string;
  onHookChange: (value: string) => void;
  pov: string;
  onPovChange: (value: string) => void;
  plotline: string;
  onPlotlineChange: (value: string) => void;
  targetWords: string;
  onTargetWordsChange: (value: string) => void;
  targetCount: number;
  keyChapter: boolean;
  onKeyChapterChange: (value: boolean) => void;
  phase: "idle" | "save" | "start";
  canEdit: boolean;
}) {
  const disabled = phase !== "idle" || !canEdit;
  return (
    <Collapse
      className="studio-beat"
      bordered={false}
      activeKey={beatOpen ? ["beat"] : []}
      onChange={(keys) =>
        onBeatOpenChange(
          Array.isArray(keys) ? keys.includes("beat") : keys === "beat",
        )
      }
      items={[
        {
          key: "beat",
          label: (
            <span className="studio-beat-summary">
              <b>本章把控</b>
              <small>
                {[
                  chapterStatusLabel(chapterStatus),
                  beatOutline.trim() ? "已设细纲" : "细纲未填",
                  hook.trim() ? "已设章尾钩" : null,
                  pov.trim() ? `POV ${pov.trim()}` : null,
                  targetCount > 0 ? `目标 ${targetCount} 字` : null,
                  keyChapter ? "关键章" : null,
                ]
                  .filter(Boolean)
                  .join(" · ")}
              </small>
            </span>
          ),
          children: (
            <div className="studio-beat-grid">
              <label className="studio-beat-full">
                <span>本章细纲（起 / 承 / 转 / 合 / 钩）</span>
                <Input.TextArea
                  aria-label="本章细纲"
                  disabled={disabled}
                  placeholder="写下本章核心节拍与冲突推进，AI 起草与审评将严格对齐"
                  value={beatOutline}
                  autoSize={{ minRows: 2, maxRows: 6 }}
                  onChange={(event) => onBeatOutlineChange(event.target.value)}
                />
              </label>
              <label className="studio-beat-full">
                <span>章尾追读钩</span>
                <Input
                  aria-label="章尾追读钩"
                  disabled={disabled}
                  placeholder="章末留下的悬念、反转或代价"
                  value={hook}
                  onChange={(event) => onHookChange(event.target.value)}
                />
              </label>
              <label>
                <span>视角人物</span>
                <Input
                  aria-label="视角人物"
                  disabled={disabled}
                  placeholder="本章主视角人物"
                  value={pov}
                  onChange={(event) => onPovChange(event.target.value)}
                />
              </label>
              <label>
                <span>所属剧情线</span>
                <Input
                  aria-label="所属剧情线"
                  disabled={disabled}
                  placeholder="例如：主线·渡口之变"
                  value={plotline}
                  onChange={(event) => onPlotlineChange(event.target.value)}
                />
              </label>
              <label>
                <span>目标字数（汉字）</span>
                <Input
                  aria-label="目标字数"
                  disabled={disabled}
                  placeholder="例如：3000"
                  value={targetWords}
                  inputMode="numeric"
                  onChange={(event) => onTargetWordsChange(event.target.value)}
                />
              </label>
              <span className="studio-beat-switch">
                <Switch
                  aria-label="关键章"
                  disabled={disabled}
                  checked={keyChapter}
                  onChange={(value) => onKeyChapterChange(value)}
                />{" "}
                关键章（重点把控高潮与兑现）
              </span>
            </div>
          ),
        },
      ]}
    />
  );
}
