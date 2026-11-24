import { useQuery } from "@tanstack/react-query";
import {
  Button,
  Checkbox,
  Form,
  Input,
  Modal,
  Select,
  Switch,
  Tabs,
} from "antd";
import { useState, type ReactNode } from "react";
import {
  adopt,
  api,
  scoped,
  type Entity,
  type Json,
} from "../../../shared/api";
import { ReferenceInput } from "../../../shared/inputs/ReferenceInput";
import {
  STAGE_LABELS,
  fetchStudioCatalog,
  normalizeStages,
  type BuiltinCommonsAttachment,
  type CrossScopeAttachment,
  type PipelineStage,
  type StudioForeshadow,
} from "../../../shared/studioApi";
import { useWorkspace } from "../../../shared/WorkspaceContext";

const PRESETS: { label: string; stages: PipelineStage[] | null }[] = [
  { label: "默认全自动", stages: null },
  { label: "单推细纲", stages: ["plan"] },
  { label: "细纲+结构审", stages: ["plan", "judge_plan"] },
  { label: "按细纲起草", stages: ["write"] },
  { label: "起草+审评+返修", stages: ["write", "judge", "revise"] },
  { label: "仅质量审评", stages: ["judge"] },
  { label: "定向返修", stages: ["revise", "judge"] },
  {
    label: "全流程合并处理",
    stages: ["plan", "judge_plan", "write", "judge", "revise"],
  },
];

const ALERT_LABEL: Record<string, string> = {
  overdue: "超期未回收",
  due_soon: "临期预警",
  active: "推进中",
  planned: "待埋设",
  resolved: "已兑现",
  dropped: "已作废",
};

export function StudioCockpit({
  scheme,
  schemeOptions,
  onScheme,
  objective,
  onObjective,
  guidance,
  onGuidance,
  stages,
  stageError,
  onStages,
  selectionOnly,
  onSelectionOnly,
  selectionReady,
  delegationId,
  delegations,
  onDelegation,
  sourceIds,
  onSourceIds,
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
  activeTab,
  onTabChange,
  hasCandidate,
  jobRunning,
  score,
  onCollapse,
}: {
  scheme: string;
  schemeOptions: { value: string; label: string }[];
  onScheme: (value: string) => void;
  objective: string;
  onObjective: (value: string) => void;
  guidance: string;
  onGuidance: (value: string) => void;
  stages: PipelineStage[] | null;
  stageError?: string | null;
  onStages: (value: PipelineStage[] | null) => void;
  selectionOnly: boolean;
  onSelectionOnly: (value: boolean) => void;
  selectionReady: boolean;
  delegationId?: string;
  delegations: { id: string; label: string }[];
  onDelegation: (value: string | undefined) => void;
  sourceIds: string[];
  onSourceIds: (value: string[]) => void;
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
  activeTab: string;
  onTabChange: (tab: string) => void;
  hasCandidate: boolean;
  jobRunning: boolean;
  score: ReactNode;
  onCollapse: () => void;
}) {
  const blockedStages =
    Boolean(stageError) ||
    (!delegationId && stages !== null && stages.length === 0);
  const blockedSelection = selectionOnly && !selectionReady;
  return (
    <aside className="studio-cockpit" aria-label="出品人工作舱">
      <div className="studio-rail-head">
        <b>出品人工作舱</b>
        <Button type="link" onClick={onCollapse}>
          收起工作舱
        </Button>
      </div>
      <Tabs
        size="small"
        tabBarGutter={14}
        activeKey={activeTab}
        onChange={onTabChange}
        items={[
          {
            key: "ai",
            label: "AI 协同",
            children: (
              <div className="studio-tab">
                <div className="studio-presets">
                  {PRESETS.map((preset) => (
                    <Button
                      key={preset.label}
                      type={
                        sameStages(stages, preset.stages)
                          ? "primary"
                          : "default"
                      }
                      onClick={() => onStages(preset.stages)}
                    >
                      {preset.label}
                    </Button>
                  ))}
                </div>
                <div className="studio-checks">
                  {(Object.keys(STAGE_LABELS) as PipelineStage[]).map(
                    (stage) => (
                      <Checkbox
                        key={stage}
                        checked={!!stages?.includes(stage)}
                        onChange={(event) => {
                          const base = stages ?? [];
                          const next = event.target.checked
                            ? [...base, stage]
                            : base.filter((item) => item !== stage);
                          onStages(next.length ? normalizeStages(next) : []);
                        }}
                      >
                        {STAGE_LABELS[stage]}
                      </Checkbox>
                    ),
                  )}
                </div>
                {stageError ? (
                  <p className="creation-note" role="alert">
                    {stageError}
                  </p>
                ) : blockedStages ? (
                  <p>先选择至少一道工序</p>
                ) : null}
                <Select
                  aria-label="评分方案"
                  disabled={phase !== "idle" || !canEdit}
                  value={scheme}
                  options={schemeOptions}
                  onChange={onScheme}
                  style={{ width: "100%" }}
                />
                <Input.TextArea
                  aria-label="创作目标"
                  autoSize={{ minRows: 3, maxRows: 8 }}
                  value={objective}
                  onChange={(event) => onObjective(event.target.value)}
                  placeholder="例如：续写渡河这一章，让主角在救人和保住身份之间做出选择。"
                />
                <Input.TextArea
                  aria-label="出品人方向指引"
                  autoSize={{ minRows: 2, maxRows: 6 }}
                  value={guidance}
                  onChange={(event) => onGuidance(event.target.value)}
                  placeholder="出品人方向指引"
                />
                <div className="studio-switch">
                  <Switch checked={selectionOnly} onChange={onSelectionOnly} />
                  <span>只改选中的段</span>
                </div>
                {blockedSelection ? <p>先在稿纸里选中要改的段</p> : null}
                {(delegations.length > 0 || delegationId) && (
                  <Select
                    aria-label="成果采用方式"
                    value={delegationId || "manual"}
                    style={{ width: "100%" }}
                    onChange={(value) =>
                      onDelegation(value === "manual" ? undefined : value)
                    }
                    options={[
                      { value: "manual", label: "完成后由我审核采用" },
                      ...delegations.map((item) => ({
                        value: item.id,
                        label: item.label,
                      })),
                    ]}
                  />
                )}
                <div className="studio-capsules">
                  {sourceIds.map((id) => (
                    <Button
                      key={id}
                      onClick={() =>
                        onSourceIds(sourceIds.filter((item) => item !== id))
                      }
                    >
                      {sourceTitles[id] || id} · 移出
                    </Button>
                  ))}
                  {builtins.map((card) => (
                    <Button
                      key={card.id}
                      onClick={() => onRemoveBuiltin(card.id)}
                    >
                      {card.title} · 移出
                    </Button>
                  ))}
                  {commonsRefs.map((card) => (
                    <Button
                      key={card.entity_id}
                      onClick={() => onRemoveCommons(card.entity_id)}
                    >
                      {card.title} · 移出
                    </Button>
                  ))}
                  {sourceIds.length + builtins.length + commonsRefs.length ===
                  0 ? (
                    <span>还没有挂载</span>
                  ) : null}
                </div>
                <ReferenceInput
                  multiple
                  value={sourceIds}
                  onChange={onSourceIds}
                />
                <Button
                  type="primary"
                  disabled={
                    !canEdit ||
                    phase !== "idle" ||
                    !policyReady ||
                    entityPending ||
                    blockedStages ||
                    blockedSelection
                  }
                  onClick={onStart}
                >
                  {phase === "start" ? "正在开始" : "开始处理"}
                </Button>
                {(jobRunning || hasCandidate) && (
                  <Button onClick={() => onTabChange("quality")}>
                    {jobRunning
                      ? "任务运行中 · 查看进度"
                      : "已有候选结果 · 去质量把控裁定"}
                  </Button>
                )}
              </div>
            ),
          },
          {
            key: "lookup",
            label: "设定速查",
            children: <CodexLookup onMount={onMountSource} />,
          },
          {
            key: "lines",
            label: "伏笔暗线",
            children: (
              <div className="studio-tab">
                {foreshadows.length === 0 ? <p>还没有伏笔</p> : null}
                {foreshadows.map((item) => (
                  <article key={item.id} className="studio-line">
                    <b>{item.name}</b>
                    <span>
                      {item.line_type || "未标线"} ·{" "}
                      {ALERT_LABEL[item.alert_state] || item.alert_state}
                    </span>
                    {item.alert_state === "overdue" ? (
                      <span>超期未回收</span>
                    ) : null}
                    <Button onClick={() => onMountSource(item.id, item.name)}>
                      挂载给 AI
                    </Button>
                  </article>
                ))}
                <Button onClick={onOpenBlueprint}>去大纲管理</Button>
              </div>
            ),
          },
          {
            key: "quality",
            label: hasCandidate ? "质量把控 · 待裁定" : "质量把控",
            children: score,
          },
        ]}
      />
    </aside>
  );
}

function sameStages(
  current: PipelineStage[] | null,
  preset: PipelineStage[] | null,
) {
  if (current === null || preset === null) return current === preset;
  if (current.length !== preset.length) return false;
  return current.every((stage, index) => stage === preset[index]);
}

function CodexLookup({
  onMount,
}: {
  onMount: (id: string, title: string) => void;
}) {
  const { scope, refresh } = useWorkspace();
  const catalog = useQuery({
    queryKey: ["studio-catalog"],
    queryFn: fetchStudioCatalog,
  });
  const [q, setQ] = useState("");
  const [groupId, setGroupId] = useState("全部");
  const [open, setOpen] = useState(false);
  const group = catalog.data?.codex_groups.find((item) => item.id === groupId);
  const search = useQuery({
    queryKey: ["scope", scope.id, "codex-search", q],
    queryFn: () =>
      api<Json>(scoped(scope.id, "/entities/search"), "POST", {
        q,
        limit: 30,
      }),
    enabled: q.trim().length > 0,
  });
  const items = ((search.data?.items || []) as Entity[]).filter((item) =>
    group ? group.kinds.includes(item.kind) : true,
  );
  return (
    <div className="studio-tab">
      <Input
        aria-label="搜索设定"
        placeholder="搜索人物、功法、丹药、场景"
        value={q}
        onChange={(event) => setQ(event.target.value)}
      />
      <div className="studio-presets">
        <Button
          type={groupId === "全部" ? "primary" : "default"}
          onClick={() => setGroupId("全部")}
        >
          全部
        </Button>
        {(catalog.data?.codex_groups || []).map((item) => (
          <Button
            key={item.id}
            type={groupId === item.id ? "primary" : "default"}
            onClick={() => setGroupId(item.id)}
          >
            {item.label}
          </Button>
        ))}
      </div>
      {search.isError ? <p>设定没有载入</p> : null}
      {items.map((item) => (
        <article key={item.id} className="studio-line">
          <b>{item.name}</b>
          <span>{item.kind}</span>
          <p>{item.text_preview || item.text.slice(0, 80)}</p>
          <Button onClick={() => onMount(item.id, item.name)}>挂载给 AI</Button>
        </article>
      ))}
      <Button onClick={() => setOpen(true)}>快建新设定</Button>
      <QuickCodex
        open={open}
        groups={catalog.data?.codex_groups || []}
        onClose={() => setOpen(false)}
        onCreated={(createdName) => {
          setOpen(false);
          setQ(createdName);
          refresh();
          search.refetch();
        }}
      />
    </div>
  );
}

function QuickCodex({
  open,
  groups,
  onClose,
  onCreated,
}: {
  open: boolean;
  groups: { id: string; label: string; kinds: string[] }[];
  onClose: () => void;
  onCreated: (name: string) => void;
}) {
  const { scope } = useWorkspace();
  const [form] = Form.useForm();
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const kinds = groups.flatMap((group) => group.kinds);
  return (
    <Modal
      title="快建新设定"
      open={open}
      onCancel={onClose}
      onOk={() => form.submit()}
      confirmLoading={saving}
      destroyOnHidden
    >
      <Form
        form={form}
        layout="vertical"
        onFinish={async (values) => {
          setSaving(true);
          setError("");
          try {
            await adopt(
              scope,
              [
                {
                  op: "create",
                  entity_id: crypto.randomUUID(),
                  kind: values.kind,
                  name: values.name,
                  text: values.text || "",
                  data: { status: "draft" },
                },
              ],
              "快建设定：" + values.name,
            );
            const createdName = String(values.name || "");
            form.resetFields();
            onCreated(createdName);
          } catch (reason) {
            setError((reason as Error).message);
          } finally {
            setSaving(false);
          }
        }}
      >
        <Form.Item name="name" label="名称" rules={[{ required: true }]}>
          <Input />
        </Form.Item>
        <Form.Item name="kind" label="类别" rules={[{ required: true }]}>
          <Select
            showSearch
            optionFilterProp="label"
            options={[...new Set(kinds)].map((value) => ({
              value,
              label: value,
            }))}
          />
        </Form.Item>
        <Form.Item name="text" label="摘要">
          <Input.TextArea autoSize={{ minRows: 3, maxRows: 6 }} />
        </Form.Item>
        {error ? <p>{error}</p> : null}
      </Form>
    </Modal>
  );
}
