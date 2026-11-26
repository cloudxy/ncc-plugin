import { DownloadOutlined } from "@ant-design/icons";
import { Button, Drawer, Segmented, Space, Tag } from "antd";
import type { ReactNode } from "react";
import type { Json } from "../../../shared/api";
import { PageTitle } from "../../../shared/components/Feedback";
import type {
  BuiltinCommonsAttachment,
  CrossScopeAttachment,
  PipelineStage,
  StudioForeshadow,
} from "../../../shared/studioApi";
import { effectDetail } from "../effectDetail";
import { ScoreCard } from "./ScoreCard";
import { StudioCockpit } from "./StudioCockpit";

export function CreativeTopHeader({
  returnTarget,
  onReturn,
  effectiveViewRole,
  canUseReaderView,
  onViewRoleChange,
  onOpenExport,
}: {
  returnTarget: { label: string; to: string } | undefined;
  onReturn: () => void;
  effectiveViewRole: "author" | "reader";
  canUseReaderView: boolean;
  onViewRoleChange: (role: "author" | "reader") => void;
  onOpenExport: () => void;
}) {
  return (
    <PageTitle
      title="创作台"
      note="说出你想写的内容。准备、检查、评分与返修交给流程。"
      actions={
        <Space wrap>
          {returnTarget ? (
            <Button onClick={onReturn}>{returnTarget.label}</Button>
          ) : null}
          <Segmented
            size="small"
            aria-label="阅读视角切换"
            value={effectiveViewRole}
            options={[
              { value: "author", label: "作者全知" },
              {
                value: "reader",
                label: "读者此刻（防剧透）",
                disabled: !canUseReaderView,
              },
            ]}
            onChange={(value) => onViewRoleChange(value as "author" | "reader")}
          />
          <Button icon={<DownloadOutlined />} onClick={onOpenExport}>
            导出成稿
          </Button>
          <Tag color="green">作者可随时接管</Tag>
        </Space>
      }
    />
  );
}

export function CreativeCockpitPane({
  scheme,
  schemeLabels,
  onSchemeChange,
  objective,
  onObjectiveChange,
  guidance,
  onGuidanceChange,
  stages,
  stageError,
  onStagesChange,
  selectionOnly,
  onSelectionOnlyChange,
  selectionReady,
  delegationId,
  availableDelegations,
  onDelegationChange,
  sourceIds,
  onSourceIdsChange,
  builtins,
  onRemoveBuiltin,
  commonsRefs,
  onRemoveCommons,
  sourceTitles,
  onMountSource,
  foreshadows,
  onOpenBlueprint,
  phase,
  canEdit,
  policyReady,
  entityPending,
  onStart,
  cockpitTab,
  onCockpitTabChange,
  hasCandidate,
  job,
  relatedJobs,
  jobsError,
  jobsLoading,
  jobsOffline,
  pendingResult,
  adopted,
  adopting,
  adoptError,
  returnLabel,
  onReturn,
  onSelectJob,
  onAdopt,
  onEditCandidate,
  onChooseCandidate,
  onRefreshJobs,
  effectiveViewRole,
  chapterId,
  onCollapse,
}: {
  scheme: string;
  schemeLabels: Record<string, string>;
  onSchemeChange: (next: string) => void;
  objective: string;
  onObjectiveChange: (value: string) => void;
  guidance: string;
  onGuidanceChange: (value: string) => void;
  stages: PipelineStage[] | null;
  stageError: string | null;
  onStagesChange: (value: PipelineStage[] | null) => void;
  selectionOnly: boolean;
  onSelectionOnlyChange: (value: boolean) => void;
  selectionReady: boolean;
  delegationId: string | undefined;
  availableDelegations: Json[];
  onDelegationChange: (value?: string) => void;
  sourceIds: string[];
  onSourceIdsChange: (ids: string[]) => void;
  builtins: BuiltinCommonsAttachment[];
  onRemoveBuiltin: (id: string) => void;
  commonsRefs: CrossScopeAttachment[];
  onRemoveCommons: (entityId: string) => void;
  sourceTitles: Record<string, string>;
  onMountSource: (id: string, title: string) => void;
  foreshadows: StudioForeshadow[];
  onOpenBlueprint: () => void;
  phase: "idle" | "save" | "start";
  canEdit: boolean;
  policyReady: boolean;
  entityPending: boolean;
  onStart: () => void;
  cockpitTab: string;
  onCockpitTabChange: (tab: string) => void;
  hasCandidate: boolean;
  job: Json | undefined;
  relatedJobs: Json[];
  jobsError: unknown;
  jobsLoading: boolean;
  jobsOffline: boolean;
  pendingResult: boolean;
  adopted: boolean;
  adopting: boolean;
  adoptError: string | undefined;
  returnLabel: string | undefined;
  onReturn: (() => void) | undefined;
  onSelectJob: (jobId: string) => void;
  onAdopt: () => void;
  onEditCandidate: (text: string, artifact: "plan" | "draft") => void;
  onChooseCandidate: (index: number) => void;
  onRefreshJobs: () => void;
  effectiveViewRole: "author" | "reader";
  chapterId: string | undefined;
  onCollapse: () => void;
}) {
  const hasJobsError = Boolean(jobsError);
  const score = (
    <ScoreCard
      job={hasJobsError ? undefined : job}
      relatedJobs={hasJobsError ? undefined : relatedJobs}
      loading={jobsLoading}
      loadError={
        hasJobsError
          ? jobsOffline
            ? "网络连接失败。恢复连接后可重试。"
            : effectDetail(jobsError)
          : undefined
      }
      offline={hasJobsError && jobsOffline}
      pending={pendingResult}
      adopted={adopted}
      adopting={adopting}
      adoptError={adoptError}
      returnLabel={returnLabel}
      onReturn={onReturn}
      onSelectJob={onSelectJob}
      onAdopt={onAdopt}
      onEdit={onEditCandidate}
      onChoose={onChooseCandidate}
      onRefresh={onRefreshJobs}
    />
  );

  return (
    <StudioCockpit
      scheme={scheme}
      schemeOptions={Object.entries(schemeLabels).map(([value, label]) => ({
        value,
        label,
      }))}
      onScheme={onSchemeChange}
      objective={objective}
      onObjective={onObjectiveChange}
      guidance={guidance}
      onGuidance={onGuidanceChange}
      stages={stages}
      stageError={stageError}
      onStages={onStagesChange}
      selectionOnly={selectionOnly}
      onSelectionOnly={onSelectionOnlyChange}
      selectionReady={selectionReady}
      delegationId={delegationId}
      delegations={availableDelegations.map((item) => ({
        id: item.id,
        label: `${item.authorization?.mode === "author_trial" ? "自动定稿试运行 · 校准未验证" : "自动定稿 · 需已校准策略"} · 剩余${item.remaining}次`,
      }))}
      onDelegation={onDelegationChange}
      sourceIds={sourceIds}
      onSourceIds={onSourceIdsChange}
      builtins={builtins}
      onRemoveBuiltin={onRemoveBuiltin}
      commonsRefs={commonsRefs}
      onRemoveCommons={onRemoveCommons}
      sourceTitles={sourceTitles}
      onMountSource={onMountSource}
      foreshadows={foreshadows}
      onOpenBlueprint={onOpenBlueprint}
      phase={phase}
      canEdit={canEdit}
      policyReady={policyReady}
      entityPending={entityPending}
      onStart={onStart}
      activeTab={cockpitTab}
      onTabChange={onCockpitTabChange}
      hasCandidate={hasCandidate}
      jobRunning={job?.state === "running" || job?.state === "queued"}
      jobQueued={job?.state === "queued"}
      viewRole={effectiveViewRole}
      chapterId={chapterId}
      score={score}
      onCollapse={onCollapse}
    />
  );
}

export function CreativeMobileDrawers({
  narrow,
  leftOpen,
  onCloseLeft,
  rightOpen,
  onCloseRight,
  rail,
  cockpit,
}: {
  narrow: boolean;
  leftOpen: boolean;
  onCloseLeft: () => void;
  rightOpen: boolean;
  onCloseRight: () => void;
  rail: ReactNode;
  cockpit: ReactNode;
}) {
  if (!narrow) return null;
  return (
    <>
      {leftOpen ? (
        <Drawer
          title="卷章与细纲目录"
          open
          onClose={onCloseLeft}
          size="default"
        >
          {rail}
        </Drawer>
      ) : null}
      {rightOpen ? (
        <Drawer title="出品人工作舱" open onClose={onCloseRight} size="large">
          {cockpit}
        </Drawer>
      ) : null}
    </>
  );
}
