import { PlayCircleOutlined, SaveOutlined } from "@ant-design/icons";
import { useQuery } from "@tanstack/react-query";
import {
  Alert,
  App,
  Button,
  Card,
  Col,
  Input,
  Row,
  Select,
  Space,
  Tag,
  Typography,
} from "antd";
import { useEffect, useRef, useState } from "react";
import { adopt, api, scoped, type Entity, type Json } from "../../shared/api";
import { ErrorPanel, PageTitle } from "../../shared/components/Feedback";
import { TextEditor } from "../../shared/components/TextEditor";
import { ReferenceInput } from "../../shared/inputs/ReferenceInput";
import { useCreationPolicy } from "../../shared/useCreationPolicy";
import { useWorkspace } from "../../shared/WorkspaceContext";
import { ScoreCard } from "./components/ScoreCard";

export function CreativePage() {
  const creationPolicy = useCreationPolicy();
  const schemeLabels = (creationPolicy.data?.scheme_labels || {}) as Record<
    string,
    string
  >;
  const { scope, refresh, setDirty } = useWorkspace(),
    { message, modal } = App.useApp();
  const draftVersion = useRef(0),
    editGeneration = useRef(0),
    draftBaseline = useRef<string | null>(null),
    draftReady = useRef(false),
    draftKey = useRef(""),
    draftQueue = useRef(Promise.resolve());
  const [draftLoaded, setDraftLoaded] = useState(false);
  const [draftStatus, setDraftStatus] = useState(""),
    [sourceIds, setSourceIds] = useState<string[]>([]),
    [selection, setSelection] = useState<[number, number]>([0, 0]);
  const [entityId, setEntityId] = useState<string>(),
    [text, setText] = useState(""),
    [baseline, setBaseline] = useState<Entity>(),
    [dirty, dirtyLocal] = useState(false);
  const [name, setName] = useState(""),
    [objective, setObjective] = useState(""),
    [scheme, setScheme] = useState("P1"),
    [busy, setBusy] = useState(false),
    [jobId, setJobId] = useState<string>();
  const [delegationId, setDelegationId] = useState<string>();
  const delegations = useQuery({
    queryKey: ["scope", scope.id, "delegations"],
    queryFn: () => api<Json[]>(scoped(scope.id, "/delegations")),
    enabled: scope.actions.includes("adopt"),
    refetchInterval: 10000,
  });
  useEffect(() => {
    setDelegationId(undefined);
  }, [entityId, scheme]);
  const entities = useQuery({
    queryKey: ["scope", scope.id, "writing-entities"],
    queryFn: () =>
      api<Json>(scoped(scope.id, "/entities/search"), "POST", { limit: 200 }),
  });
  const entity = useQuery({
    queryKey: ["scope", scope.id, "entity", entityId],
    queryFn: () => api<Entity>(scoped(scope.id, `/entities/${entityId}`)),
    enabled: !!entityId,
  });
  const revisionScheme =
    creationPolicy.data?.revision_schemes?.[
      entity.data?.kind || baseline?.kind || "chapter"
    ] || "P3";
  const availableDelegations = (delegations.data || []).filter(
    (d) =>
      !d.revoked &&
      d.remaining > 0 &&
      new Date(d.expires_at).getTime() > Date.now() &&
      d.target_ids.includes(entityId) &&
      d.schemes.includes(scheme) &&
      (scheme !== "P5" || d.schemes.includes(revisionScheme)),
  );
  const jobs = useQuery({
    queryKey: ["scope", scope.id, "jobs"],
    queryFn: () => api<Json[]>(scoped(scope.id, "/jobs")),
    refetchInterval: 2500,
  });
  const job =
    jobs.data?.find((j) => j.id === jobId) ||
    jobs.data?.find((j) => j.kind === "creation" && j.state !== "applied");
  useEffect(() => {
    if (entity.data && !dirty) {
      setBaseline(entity.data);
      setText(entity.data.text);
      setName(entity.data.name);
    }
  }, [entity.data]);
  useEffect(() => () => setDirty(false), []);
  useEffect(() => {
    let live = true;
    draftReady.current = false;
    setDraftLoaded(false);
    editGeneration.current = 0;
    draftVersion.current = 0;
    draftBaseline.current = null;
    draftKey.current = scope.id + ":" + (entityId || "new");
    api<Json>(scoped(scope.id, `/author-drafts/${entityId || "new"}`))
      .then((d) => {
        if (!live) return;
        draftVersion.current = d.version;
        draftBaseline.current = d.baseline || null;
        draftReady.current = true;
        setDraftLoaded(true);
        if (d.text && editGeneration.current === 0) {
          setText(d.text);
          setName(d.name);
          setScheme(d.scheme);
          dirtyLocal(true);
          setDirty(true);
          setDraftStatus("已恢复自动保存的草稿");
        }
      })
      .catch((e) => {
        if (live) setDraftStatus(e.message);
      });
    return () => {
      live = false;
    };
  }, [scope.id, entityId]);
  useEffect(() => {
    if (!dirty || !draftLoaded || !draftReady.current || busy) return;
    let live = true;
    const key = draftKey.current;
    const timer = setTimeout(() => {
      setDraftStatus("正在保存草稿");
      draftQueue.current = draftQueue.current
        .then(async () => {
          if (key !== draftKey.current) return;
          const d = await api<Json>(
            scoped(scope.id, `/author-drafts/${entityId || "new"}`),
            "PUT",
            {
              version: draftVersion.current,
              entity_id: entityId || null,
              baseline:
                draftBaseline.current ||
                baseline?.version ||
                entity.data?.version ||
                null,
              name,
              text,
              scheme,
            },
          );
          if (key === draftKey.current) {
            draftVersion.current = d.version;
            if (live) setDraftStatus("草稿已自动保存");
          }
        })
        .catch((e) => {
          if (live) setDraftStatus(e.message);
        });
    }, 1500);
    return () => {
      live = false;
      clearTimeout(timer);
    };
  }, [text, name, scheme, dirty, entityId, busy, draftLoaded]);
  function update(value: string) {
    editGeneration.current += 1;
    setText(value);
    dirtyLocal(true);
    setDirty(true);
  }
  async function save() {
    setBusy(true);
    try {
      await draftQueue.current;
      const original = baseline || entity.data;
      if (entityId && !original) throw new Error("对象尚在读取，请稍后保存");
      const operation = original
        ? {
            op: "update",
            entity_id: original.id,
            expected: draftBaseline.current || original.version,
            text,
            name: name || original.name,
          }
        : {
            op: "create",
            entity_id: crypto.randomUUID(),
            kind: "chapter",
            name: name || "新章节",
            text,
            data: { status: "draft" },
          };
      await adopt(scope, [operation], "作者保存修订：" + (name || "新章节"));
      try {
        await api(
          scoped(
            scope.id,
            `/author-drafts/${entityId || "new"}?version=${draftVersion.current}`,
          ),
          "DELETE",
        );
        draftVersion.current += 1;
      } catch (e) {
        message.info("正式版本已保存；未清理的草稿已保留供比较");
      }
      setEntityId(operation.entity_id);
      draftBaseline.current = null;
      dirtyLocal(false);
      setDirty(false);
      setBaseline(undefined);
      refresh();
      message.success("新修订已保存；旧评分将重新检查有效性");
      return operation.entity_id;
    } catch (e) {
      message.error((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function generate(mode = "create", selectedOnly = false) {
    if (!creationPolicy.data) {
      message.error("评分方案尚未载入，请稍后重试");
      creationPolicy.refetch();
      return;
    }
    if (mode === "create" && !objective.trim()) {
      message.info("写下一句话，告诉AI这次要完成什么");
      return;
    }
    if (
      mode === "create" &&
      delegationId &&
      !availableDelegations.some((d) => d.id === delegationId)
    ) {
      message.error("自动定稿授权已变化，请重新选择或改为人工审核");
      delegations.refetch();
      return;
    }
    setBusy(true);
    try {
      let targetId = entityId;
      if (dirty) {
        targetId = await save();
        if (!targetId) return;
      }
      if (mode === "assess" && !targetId) {
        message.info("先保存内容，再单独评分");
        return;
      }
      const kinds: Record<string, string> = {
        P1: "chapter",
        P2: "outline",
        P3: "character",
        P4: "source",
        P5: baseline?.kind || "chapter",
      };
      const created = await api<Json>(
        scoped(scope.id, "/creation-tasks"),
        "POST",
        {
          objective: objective || "评价当前内容，提供分项证据和修改建议",
          scheme,
          mode,
          kind: baseline?.kind || kinds[scheme],
          name: name || "创作候选",
          entity_id: targetId || null,
          delegation_id: mode === "create" ? delegationId || null : null,
          source_ids: sourceIds,
          selection_start: selectedOnly
            ? Array.from(text.slice(0, selection[0])).length
            : null,
          selection_end: selectedOnly
            ? Array.from(text.slice(0, selection[1])).length
            : null,
          max_revisions: mode === "assess" ? 0 : 2,
          token_budget: 24000,
        },
      );
      setJobId(created.id);
      jobs.refetch();
      message.success("已进入自动创作流程");
    } catch (e) {
      message.error((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function adoptCandidate() {
    if (!job) return;
    const run = async () => {
      try {
        await api(scoped(scope.id, `/jobs/${job.id}/adopt`), "POST");
        refresh();
        jobs.refetch();
        message.success("成果及关联资料已采用");
      } catch (e) {
        message.error((e as Error).message);
      }
    };
    const candidate =
      job.result?.candidates?.[
        job.result?.selected ?? job.result?.candidates.length - 1
      ];
    if (candidate?.evaluation?.verdict !== "qualified")
      modal.confirm({
        title: "采用你选择的版本",
        content:
          "此版本未达到自动质量线。采用会保留原评分及作者选择记录，硬伤和版本检查仍会执行。",
        onOk: run,
      });
    else await run();
  }
  return (
    <>
      <PageTitle
        title="创作台"
        note="说出你想写的内容。准备、检查、评分与返修交给流程。"
        actions={<Tag color="green">作者可随时接管</Tag>}
      />
      <Row gutter={24}>
        <Col xs={24} xl={17}>
          <Card
            className="writing-card"
            title={
              <Space>
                <Select
                  aria-label="编辑对象"
                  allowClear
                  placeholder="选择已有内容，或开始新稿"
                  value={entityId}
                  style={{ width: 260 }}
                  showSearch
                  optionFilterProp="label"
                  options={entities.data?.items.map((e: Entity) => ({
                    value: e.id,
                    label: e.name,
                  }))}
                  onChange={(value) => {
                    if (dirty) {
                      modal.confirm({
                        title: "离开未保存的编辑？",
                        onOk: () => {
                          dirtyLocal(false);
                          setDirty(false);
                          setBaseline(undefined);
                          setEntityId(value);
                          setText("");
                        },
                      });
                    } else {
                      setBaseline(undefined);
                      setEntityId(value);
                      setText("");
                    }
                  }}
                />
                <Tag>
                  {dirty ? "未保存修改" : baseline ? "已保存修订" : "新稿"}
                </Tag>
              </Space>
            }
            extra={
              <Button
                loading={busy}
                disabled={!scope.actions.includes("edit") || !text.trim()}
                icon={<SaveOutlined />}
                onClick={save}
              >
                保存修订
              </Button>
            }
          >
            <ErrorPanel error={entity.error || entities.error} />
            {dirty &&
              entity.data &&
              baseline?.version !== entity.data.version && (
                <Alert
                  type="warning"
                  title="后台已有新修订，你的修改已保留。保存时需要比较版本。"
                />
              )}
            <Input
              className="chapter-title"
              aria-label="稿件名称"
              disabled={busy || !scope.actions.includes("edit")}
              variant="borderless"
              value={name}
              onChange={(e) => {
                editGeneration.current += 1;
                setName(e.target.value);
                dirtyLocal(true);
                setDirty(true);
              }}
              placeholder="给这一章或这份内容起个名字"
            />
            <TextEditor
              value={text}
              readOnly={busy || !scope.actions.includes("edit")}
              onChange={update}
              onSelection={(from, to) => setSelection([from, to])}
              height={490}
            />
            <div className="editor-footer">
              <span>
                {draftStatus} · {text.replace(/\s/g, "").length} 字符 ·
                新版本保留修改历史
              </span>
              <span>正文变动后，旧评分不沿用</span>
            </div>
          </Card>
          <Card className="intent-card" style={{ marginTop: 20 }}>
            <div className="intent-title">
              <Typography.Text strong>这次想完成什么？</Typography.Text>
              <Select
                value={scheme}
                style={{ width: 160 }}
                options={Object.entries(schemeLabels).map(([value, label]) => ({
                  value,
                  label,
                }))}
                onChange={setScheme}
              />
            </div>
            <Input.TextArea
              aria-label="创作目标"
              autoSize={{ minRows: 3, maxRows: 8 }}
              value={objective}
              onChange={(e) => setObjective(e.target.value)}
              placeholder="例如：续写渡河这一章，让主角在救人和保住身份之间做出选择。"
            />
            <div style={{ marginTop: 12 }}>
              <ReferenceInput
                multiple
                value={sourceIds}
                onChange={setSourceIds}
              />
            </div>
            {(availableDelegations.length > 0 || delegationId) && (
              <div style={{ marginTop: 12 }}>
                <Select
                  aria-label="成果采用方式"
                  value={delegationId || "manual"}
                  style={{ width: "100%" }}
                  onChange={(v) =>
                    setDelegationId(v === "manual" ? undefined : v)
                  }
                  options={[
                    { value: "manual", label: "完成后由我审核采用" },
                    ...availableDelegations.map((d) => ({
                      value: d.id,
                      label: `${d.authorization?.mode === "author_trial" ? "自动定稿试运行 · 校准未验证" : "自动定稿 · 需已校准策略"} · 剩余${d.remaining}次`,
                    })),
                  ]}
                />
              </div>
            )}
            <div className="intent-actions">
              <Space>
                <Button
                  disabled={busy || !creationPolicy.data || !text.trim()}
                  onClick={() => generate("assess")}
                >
                  仅评分
                </Button>
                <Button
                  disabled={
                    busy ||
                    !creationPolicy.data ||
                    selection[0] === selection[1]
                  }
                  onClick={() => generate("create", true)}
                >
                  改写选段
                </Button>
              </Space>
              <span>
                自动检查与评分 · 最多修订2次 ·{" "}
                {delegationId ? "达标后按授权自动定稿" : "成果集中审核"}
              </span>
              <Button
                type="primary"
                size="large"
                loading={busy}
                disabled={
                  !scope.actions.includes("edit") ||
                  !creationPolicy.data ||
                  (!!entityId && entity.isPending)
                }
                icon={<PlayCircleOutlined />}
                onClick={() => generate()}
              >
                开始处理
              </Button>
            </div>
          </Card>
        </Col>
        <Col xs={24} xl={7}>
          <ScoreCard
            job={job}
            onAdopt={adoptCandidate}
            onEdit={(value) => {
              update(value);
              message.info("已放入编辑器。保存新修订后重新评估。");
            }}
            onRefresh={() => jobs.refetch()}
          />
          <Card style={{ marginTop: 20 }} size="small" title="本次操作边界">
            <Typography.Paragraph type="secondary">
              生成与返修保留原稿。主线偏离、关键冲突和未解决问题集中交给你决定。采用内容不会自动对外发布。
            </Typography.Paragraph>
          </Card>
        </Col>
      </Row>
    </>
  );
}
