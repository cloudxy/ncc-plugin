import { Button, Card, Input } from "antd";
import type { RefObject } from "react";
import type { Entity } from "../../../shared/api";
import type { ChapterStatus } from "../../../shared/chapterStatus";
import {
  TextEditor,
  type TextEditorHandle,
} from "../../../shared/components/TextEditor";
import type { StudioChapter } from "../../../shared/studioApi";
import { BeatControlBar } from "./BeatControlBar";
import { ChapterToolbarExtra, ChapterToolbarTitle } from "./ChapterToolbar";
import {
  ConflictRecoveryBanner,
  ReaderPerspectiveBanner,
} from "./ConflictRecoveryBanner";

export type WritingBeatFields = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  chapterStatus: ChapterStatus;
  beatOutline: string;
  hook: string;
  pov: string;
  plotline: string;
  targetWords: string;
  targetCount: number;
  keyChapter: boolean;
  onPatch: (
    field:
      | "chapter_status"
      | "beat_outline"
      | "hook"
      | "pov"
      | "plotline"
      | "target_words"
      | "key_chapter",
    value: string | boolean,
  ) => void;
};

export function WritingSheetPane({
  narrow,
  leftOpen,
  rightOpen,
  onOpenLeft,
  onOpenRight,
  effectiveViewRole,
  onExitReaderView,
  entityId,
  jobId,
  options,
  isNonChapterTarget,
  phase,
  canEdit,
  dirty,
  hasBaseline,
  latestChapter,
  onChooseEntity,
  focus,
  onToggleFocus,
  onSave,
  loadError,
  onRetryLoad,
  currentEntityKind,
  onOpenMaterials,
  hasEntityConflict,
  serverEntity,
  activeBaselineVersion,
  text,
  onTextChange,
  onAdoptServerLatest,
  onSaveOverServerLatest,
  beat,
  name,
  onNameChange,
  editorRef,
  onSelectionChange,
  draftStatus,
  hanLabel,
  hanCount,
}: {
  narrow: boolean;
  leftOpen: boolean;
  rightOpen: boolean;
  onOpenLeft: () => void;
  onOpenRight: () => void;
  effectiveViewRole: "author" | "reader";
  onExitReaderView: () => void;
  entityId: string | undefined;
  jobId: string | undefined;
  options: { value: string; label: string; status?: string }[];
  isNonChapterTarget: boolean;
  phase: "idle" | "save" | "start";
  canEdit: boolean;
  dirty: boolean;
  hasBaseline: boolean;
  latestChapter: StudioChapter | undefined;
  onChooseEntity: (value?: string) => void;
  focus: boolean;
  onToggleFocus: () => void;
  onSave: () => void;
  loadError: unknown;
  onRetryLoad: () => void;
  currentEntityKind: string | undefined;
  onOpenMaterials: () => void;
  hasEntityConflict: boolean;
  serverEntity: Entity | undefined;
  activeBaselineVersion: string | undefined;
  text: string;
  onTextChange: (value: string) => void;
  onAdoptServerLatest: () => void;
  onSaveOverServerLatest: (ver: string) => void;
  beat: WritingBeatFields;
  name: string;
  onNameChange: (val: string) => void;
  editorRef: RefObject<TextEditorHandle | null>;
  onSelectionChange: (from: number, to: number) => void;
  draftStatus: string;
  hanLabel: string;
  hanCount: number;
}) {
  return (
    <div className="studio-sheet">
      {narrow ? (
        <div className="studio-narrow-tools">
          <Button onClick={onOpenLeft}>目录</Button>
          <Button onClick={onOpenRight}>工作舱</Button>
        </div>
      ) : null}
      {!narrow && !leftOpen ? (
        <Button onClick={onOpenLeft}>展开目录</Button>
      ) : null}
      {!narrow && !rightOpen ? (
        <Button onClick={onOpenRight}>展开工作舱</Button>
      ) : null}
      {effectiveViewRole === "reader" && (
        <ReaderPerspectiveBanner onExitReaderView={onExitReaderView} />
      )}
      <Card
        className="writing-card"
        title={
          <ChapterToolbarTitle
            entityId={entityId}
            jobId={jobId}
            options={options}
            isNonChapterTarget={isNonChapterTarget}
            chapterStatus={beat.chapterStatus}
            phase={phase}
            canEdit={canEdit}
            dirty={dirty}
            hasBaseline={hasBaseline}
            latestChapter={latestChapter}
            onChooseEntity={onChooseEntity}
            onStatusChange={(next) => beat.onPatch("chapter_status", next)}
          />
        }
        extra={
          <ChapterToolbarExtra
            focus={focus}
            canEdit={canEdit}
            phase={phase}
            onToggleFocus={onToggleFocus}
            onSave={onSave}
          />
        }
      >
        <ConflictRecoveryBanner
          loadError={loadError}
          onRetryLoad={onRetryLoad}
          canEdit={canEdit}
          isNonChapterTarget={isNonChapterTarget}
          currentEntityKind={currentEntityKind}
          onOpenMaterials={onOpenMaterials}
          hasEntityConflict={hasEntityConflict}
          serverEntity={serverEntity}
          activeBaselineVersion={activeBaselineVersion}
          localText={text}
          phase={phase}
          onAdoptServerLatest={onAdoptServerLatest}
          onSaveOverServerLatest={onSaveOverServerLatest}
        />
        {!isNonChapterTarget && (
          <BeatControlBar
            beatOpen={beat.open}
            onBeatOpenChange={beat.onOpenChange}
            chapterStatus={beat.chapterStatus}
            beatOutline={beat.beatOutline}
            onBeatOutlineChange={(val) => beat.onPatch("beat_outline", val)}
            hook={beat.hook}
            onHookChange={(val) => beat.onPatch("hook", val)}
            pov={beat.pov}
            onPovChange={(val) => beat.onPatch("pov", val)}
            plotline={beat.plotline}
            onPlotlineChange={(val) => beat.onPatch("plotline", val)}
            targetWords={beat.targetWords}
            onTargetWordsChange={(val) => beat.onPatch("target_words", val)}
            targetCount={beat.targetCount}
            keyChapter={beat.keyChapter}
            onKeyChapterChange={(val) => beat.onPatch("key_chapter", val)}
            phase={phase}
            canEdit={canEdit}
          />
        )}
        <Input
          className="chapter-title"
          aria-label="稿件名称"
          disabled={phase !== "idle" || !canEdit}
          variant="borderless"
          value={name}
          onChange={(event) => onNameChange(event.target.value)}
          placeholder="给这一章或这份内容起个名字"
        />
        <TextEditor
          ref={editorRef}
          value={text}
          readOnly={phase !== "idle" || !canEdit}
          onChange={onTextChange}
          onSelection={onSelectionChange}
          fitContent
        />
        <div className="editor-footer">
          <span>
            {draftStatus} · {hanLabel}
            {beat.targetCount > 0 && hanCount >= beat.targetCount
              ? " · 已达到目标"
              : ""}
          </span>
          <span>正文变动后，旧评分不沿用</span>
        </div>
      </Card>
    </div>
  );
}
