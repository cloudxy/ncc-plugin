import { Alert, Button, Space } from "antd";
import type { Entity } from "../../../shared/api";
import { ErrorPanel } from "../../../shared/components/Feedback";

export function ReaderPerspectiveBanner({
  onExitReaderView,
}: {
  onExitReaderView: () => void;
}) {
  return (
    <Alert
      className="studio-reader-banner"
      type="info"
      showIcon
      title="当前处于「读者此刻（防剧透）」视角：目录、设定速查与伏笔暗线已按本章阅读进度自动裁剪，隐藏后续未登场章节、暗线与作者秘密。"
      action={
        <Button size="small" onClick={onExitReaderView}>
          切回作者全知
        </Button>
      }
    />
  );
}

export function ConflictRecoveryBanner({
  loadError,
  onRetryLoad,
  canEdit,
  isNonChapterTarget,
  currentEntityKind,
  onOpenMaterials,
  hasEntityConflict,
  serverEntity,
  activeBaselineVersion,
  localText,
  phase,
  onAdoptServerLatest,
  onSaveOverServerLatest,
}: {
  loadError: unknown;
  onRetryLoad: () => void;
  canEdit: boolean;
  isNonChapterTarget: boolean;
  currentEntityKind: string | undefined;
  onOpenMaterials: () => void;
  hasEntityConflict: boolean;
  serverEntity: Entity | undefined;
  activeBaselineVersion: string | undefined;
  localText: string;
  phase: "idle" | "save" | "start";
  onAdoptServerLatest: () => void;
  onSaveOverServerLatest: (latestVersion: string) => void;
}) {
  return (
    <>
      <ErrorPanel error={loadError} retry={onRetryLoad} />
      {!canEdit && <p className="creation-note">当前范围不能编辑</p>}
      {isNonChapterTarget && (
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 12 }}
          title={`当前打开的是「${currentEntityKind}」条目，创作台仅面向正文章节写作；设定与结构属性建议前往「作品资料」抽屉编辑。`}
          action={
            <Button size="small" onClick={onOpenMaterials}>
              去作品资料
            </Button>
          }
        />
      )}
      {hasEntityConflict && serverEntity && (
        <Alert
          type="warning"
          showIcon
          title="这一章在别处更新了。你的字还在编辑器里。"
          description={
            <div>
              <p>
                <b>服务器最新版本（{serverEntity.version}）：</b>
                正文「
                {(serverEntity.text || "").slice(0, 80) || "（空）"}
                {(serverEntity.text || "").length > 80 ? "…" : ""}」
              </p>
              <p>
                <b>你的本地草稿（基于 {activeBaselineVersion}）：</b>
                正文「{localText.slice(0, 80) || "（空）"}
                {localText.length > 80 ? "…" : ""}」
              </p>
              <Space wrap>
                <Button size="small" onClick={onAdoptServerLatest}>
                  采用服务器最新版
                </Button>
                <Button
                  size="small"
                  type="primary"
                  disabled={!canEdit || phase !== "idle"}
                  onClick={() => onSaveOverServerLatest(serverEntity.version)}
                >
                  基于新版保存我的修改
                </Button>
              </Space>
            </div>
          }
        />
      )}
    </>
  );
}
