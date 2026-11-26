import { Alert, App, Button, Input, Modal, Popconfirm, Space, Tag } from "antd";
import { useEffect, useState } from "react";
import { adopt, api, scoped, type Json, type Scope } from "../../../shared/api";
import { Status } from "../../../shared/components/Feedback";
import {
  deleteBlueprintDraft,
  getBlueprintDraft,
  setBlueprintDraft,
  type StudioOutline,
  type StudioVolume,
} from "../../../shared/studioApi";
import { useWorkspace } from "../../../shared/WorkspaceContext";
import { effectDetail } from "../../creation/effectDetail";
import type { TrackedBlueprintTask } from "../blueprintTypes";

export function BlueprintTaskBanner({
  rows,
  workerOffline,
  onJumpToWork,
  onDismiss,
}: {
  rows: (TrackedBlueprintTask & { job?: Json })[];
  workerOffline: boolean;
  onJumpToWork: (item: TrackedBlueprintTask) => void;
  onDismiss: (jobId: string) => void;
}) {
  if (!rows.length) return null;
  return (
    <Alert
      type={workerOffline ? "warning" : "info"}
      showIcon
      title="AI 推演任务进度"
      description={
        <div className="blueprint-task-list">
          {workerOffline && (
            <p style={{ margin: "0 0 6px" }}>
              检测到后台任务 Worker 离线，请在终端运行 <code>./start.py</code>{" "}
              一键同启 Web 与 Worker。
            </p>
          )}
          {rows.map((item) => (
            <div key={item.jobId} className="blueprint-task-row">
              <Space wrap>
                <b>{item.label}</b>
                {item.job ? (
                  <Status value={item.job.state} />
                ) : (
                  <Tag>已提交</Tag>
                )}
                {(item.job?.error?.detail ||
                  item.job?.result?.error?.detail) && (
                  <span>
                    {item.job.error?.detail || item.job.result?.error?.detail}
                  </span>
                )}
              </Space>
              <Space size={6}>
                <Button
                  size="small"
                  type="primary"
                  onClick={() => onJumpToWork(item)}
                >
                  到创作台查看推演结果
                </Button>
                <Button size="small" onClick={() => onDismiss(item.jobId)}>
                  收起
                </Button>
              </Space>
            </div>
          ))}
        </div>
      }
    />
  );
}

export function VolumeCard({
  volume,
  isFirst,
  isLast,
  chapterCount,
  canEdit,
  onMove,
  onArchive,
  onSaved,
}: {
  volume: StudioVolume;
  isFirst: boolean;
  isLast: boolean;
  chapterCount: number;
  canEdit: boolean;
  onMove: (volume: StudioVolume, direction: -1 | 1) => void;
  onArchive: (volume: StudioVolume) => void;
  onSaved: () => void;
}) {
  const { scope } = useWorkspace();
  const { message } = App.useApp();
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [editName, setEditName] = useState(volume.name);
  const [editText, setEditText] = useState(volume.text || "");

  async function handleSave() {
    if (!editName.trim()) return;
    setSaving(true);
    try {
      const fresh = await api<Scope>(scoped(scope.id, ""));
      await adopt(
        fresh,
        [
          {
            op: "update",
            entity_id: volume.id,
            expected: volume.version,
            name: editName.trim(),
            text: editText,
          },
        ],
        "编辑分卷：" + editName.trim(),
      );
      setEditing(false);
      message.success("分卷与卷纲已保存");
      onSaved();
    } catch (error) {
      message.error(effectDetail(error));
    } finally {
      setSaving(false);
    }
  }

  return (
    <article className="blueprint-card">
      <div className="blueprint-card-head">
        <div>
          <h3>{volume.name}</h3>
          <small style={{ color: "#3e5147" }}>
            {`分卷 · 排序号 ${volume.position} · 含 ${chapterCount} 章`}
          </small>
        </div>
        <Space wrap size={6}>
          <Button
            size="small"
            disabled={!canEdit}
            onClick={() => {
              setEditName(volume.name);
              setEditText(volume.text || "");
              setEditing(true);
            }}
          >
            编辑分卷与卷纲
          </Button>
          <Button
            size="small"
            disabled={!canEdit || isFirst}
            onClick={() => onMove(volume, -1)}
          >
            上移
          </Button>
          <Button
            size="small"
            disabled={!canEdit || isLast}
            onClick={() => onMove(volume, 1)}
          >
            下移
          </Button>
          <Popconfirm
            title={`归档分卷「${volume.name}」？`}
            description="归档后本卷所属章节不会删除，将自动移回「未归卷」分组。"
            okText="确认归档"
            cancelText="取消"
            disabled={!canEdit}
            onConfirm={() => onArchive(volume)}
          >
            <Button size="small" danger disabled={!canEdit}>
              归档分卷
            </Button>
          </Popconfirm>
        </Space>
      </div>
      {volume.text ? (
        <p style={{ whiteSpace: "pre-wrap", margin: "8px 0 0" }}>
          {volume.text}
        </p>
      ) : (
        <p style={{ color: "#3e5147", margin: "8px 0 0" }}>
          尚未填写本卷卷纲与核心冲突推进
        </p>
      )}
      <Modal
        title="编辑分卷与卷纲"
        open={editing}
        onCancel={() => setEditing(false)}
        onOk={() => void handleSave()}
        okText="保存分卷"
        confirmLoading={saving}
        okButtonProps={{ disabled: !canEdit || !editName.trim() }}
        destroyOnHidden
      >
        <Space orientation="vertical" style={{ width: "100%" }} size={12}>
          <div>
            <div style={{ marginBottom: 4 }}>分卷名称</div>
            <Input
              aria-label="编辑分卷名称"
              maxLength={256}
              value={editName}
              onChange={(event) => setEditName(event.target.value)}
            />
          </div>
          <div>
            <div style={{ marginBottom: 4 }}>本卷卷纲与主线冲突</div>
            <Input.TextArea
              aria-label="本卷卷纲"
              rows={6}
              placeholder="概括本卷起承转合、阶段兑现与卷末大高潮"
              value={editText}
              onChange={(event) => setEditText(event.target.value)}
            />
          </div>
        </Space>
      </Modal>
    </article>
  );
}

export function OutlineEditor({
  outline,
  canEdit,
  onDirtyChange,
  onSaved,
}: {
  outline: StudioOutline;
  canEdit: boolean;
  onDirtyChange: () => void;
  onSaved: () => void;
}) {
  const { scope, sessionKey } = useWorkspace();
  const { message } = App.useApp();
  const cached = getBlueprintDraft(
    sessionKey,
    scope.id,
    scope.actions,
    "outline",
    outline.id,
  );
  const [beat, setBeat] = useState(
    cached ? cached.first : outline.beat_outline,
  );
  const [plotline, setPlotline] = useState(
    cached ? cached.second : outline.plotline,
  );
  const [baseVersion, setBaseVersion] = useState(
    cached ? cached.baseVersion : outline.version,
  );
  const [dirty, setDirty] = useState(Boolean(cached));
  const [conflictTriggered, setConflictTriggered] = useState(false);

  useEffect(() => {
    if (dirty) return;
    setBeat(outline.beat_outline);
    setPlotline(outline.plotline);
    setBaseVersion(outline.version);
  }, [outline.version, outline.beat_outline, outline.plotline, dirty]);

  const hasConflict =
    dirty && (outline.version !== baseVersion || conflictTriggered);

  function updateDraft(nextBeat: string, nextPlotline: string) {
    const pinned = dirty ? baseVersion : outline.version;
    setBeat(nextBeat);
    setPlotline(nextPlotline);
    setBaseVersion(pinned);
    setDirty(true);
    setBlueprintDraft(
      sessionKey,
      scope.id,
      scope.actions,
      "outline",
      outline.id,
      {
        baseVersion: pinned,
        first: nextBeat,
        second: nextPlotline,
      },
    );
    onDirtyChange();
  }

  async function saveWithExpected(expectedVersion: string) {
    try {
      await adopt(
        scope,
        [
          {
            op: "update",
            entity_id: outline.id,
            expected: expectedVersion,
            data: { beat_outline: beat, plotline },
          },
        ],
        "保存总纲：" + outline.name,
      );
      deleteBlueprintDraft(sessionKey, scope.id, "outline", outline.id);
      setDirty(false);
      setConflictTriggered(false);
      onDirtyChange();
      message.success("总纲已保存");
      onSaved();
    } catch (error) {
      const detail = effectDetail(error);
      const status = (error as { status?: number })?.status;
      if (status === 409 || status === 412) {
        setConflictTriggered(true);
        onSaved();
      }
      message.error(detail);
    }
  }

  return (
    <article className="blueprint-card">
      <h3>{outline.name}</h3>
      {hasConflict ? (
        <Alert
          type="warning"
          showIcon
          title="检测到并发更新冲突：其他窗口已保存新版本，你的草稿尚未覆盖服务器内容。"
          description={
            <div>
              <p>
                <b>服务器最新版本（{outline.version}）：</b>
                细纲「{outline.beat_outline || "（空）"}」 · 剧情走向「
                {outline.plotline || "（空）"}」
              </p>
              <p>
                <b>你的本地草稿（基于 {baseVersion}）：</b>
                细纲「{beat || "（空）"}」 · 剧情走向「{plotline || "（空）"}」
              </p>
              <Space wrap>
                <Button
                  size="small"
                  onClick={() => {
                    deleteBlueprintDraft(
                      sessionKey,
                      scope.id,
                      "outline",
                      outline.id,
                    );
                    setBeat(outline.beat_outline);
                    setPlotline(outline.plotline);
                    setBaseVersion(outline.version);
                    setDirty(false);
                    setConflictTriggered(false);
                    onDirtyChange();
                  }}
                >
                  采用服务器最新版
                </Button>
                <Button
                  size="small"
                  type="primary"
                  disabled={!canEdit || outline.version === baseVersion}
                  onClick={() => saveWithExpected(outline.version)}
                >
                  基于新版保存我的草稿
                </Button>
              </Space>
            </div>
          }
        />
      ) : null}
      <Input.TextArea
        aria-label="总纲细纲"
        value={beat}
        autoSize={{ minRows: 3, maxRows: 8 }}
        onChange={(event) => updateDraft(event.target.value, plotline)}
      />
      <Input
        aria-label="剧情走向"
        value={plotline}
        onChange={(event) => updateDraft(beat, event.target.value)}
      />
      <p>五拍：起、承、转、合、钩。主线写在剧情走向。</p>
      <Button
        disabled={!canEdit || hasConflict}
        onClick={() => saveWithExpected(baseVersion)}
      >
        保存总纲
      </Button>
    </article>
  );
}
