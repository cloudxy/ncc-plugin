import { PlusOutlined } from "@ant-design/icons";
import { useQuery } from "@tanstack/react-query";
import {
  Alert,
  App,
  Button,
  Card,
  Checkbox,
  Form,
  Input,
  InputNumber,
  Modal,
  Select,
  Skeleton,
  Space,
  Table,
} from "antd";
import { Suspense, useMemo, useRef, useState } from "react";
import {
  adopt,
  api,
  scoped,
  type Definition,
  type Entity,
  type Json,
} from "../../shared/api";
import { NoData, PageTitle } from "../../shared/components/Feedback";
import { ReferenceInput } from "../../shared/inputs/ReferenceInput";
import { scopeLine } from "../../shared/scopeLabel";
import { useWorkspace } from "../../shared/WorkspaceContext";
import { effectDetail } from "../creation/effectDetail";
import { Graph } from "./components/KnowledgeVisuals";
import "./visuals/boards.css";
import { useViewportWidth } from "./visuals/useViewportWidth";
import type { GraphEdge, GraphNode } from "./visuals/GraphCanvas";

export function RelationsPage() {
  const { scope, refresh } = useWorkspace(),
    { message } = App.useApp(),
    width = useViewportWidth(),
    [category, setCategory] = useState("relation"),
    [calendar, setCalendar] = useState(""),
    [worldAt, setWorldAt] = useState(""),
    [asOf, setAsOf] = useState<number>(),
    [open, setOpen] = useState(false),
    [form] = Form.useForm(),
    [graph, setGraph] = useState<string>(),
    [transfer, setTransfer] = useState<Json>();
  const scopeSeen = useRef(scope.id);
  if (scopeSeen.current !== scope.id) {
    scopeSeen.current = scope.id;
    setGraph(undefined);
  }
  const canEdit = scope.actions.includes("edit");
  const [transferForm] = Form.useForm();
  const defs = useQuery({
    queryKey: ["scope", scope.id, "definitions"],
    queryFn: () => api<Definition[]>(scoped(scope.id, "/definitions")),
    retry: false,
  });
  const entities = useQuery({
    queryKey: ["scope", scope.id, "relation-labels"],
    queryFn: () =>
      api<Json>(scoped(scope.id, "/entities/search"), "POST", { limit: 200 }),
    retry: false,
  });
  const labels = new Map<string, string>(
    entities.data?.items.map((e: Entity) => [e.id, e.name]),
  );
  const query = useQuery({
    queryKey: ["scope", scope.id, "facts", category, calendar, worldAt, asOf],
    retry: false,
    queryFn: () =>
      api<Json>(scoped(scope.id, "/state/query"), "POST", {
        category,
        calendar: calendar || null,
        world_at: worldAt || null,
        as_of: asOf,
        limit: 200,
      }),
  });
  const graphQuery = useQuery({
    queryKey: ["scope", scope.id, "graph", graph ?? ""],
    enabled: Boolean(graph),
    retry: false,
    queryFn: () => api<Json>(scoped(scope.id, `/graph/${graph}`)),
  });
  const graphData = graphQuery.isSuccess ? graphQuery.data : undefined;
  const factItems: Json[] = query.isSuccess ? (query.data?.items ?? []) : [];
  const graphNodes = useMemo<GraphNode[]>(() => {
    const rows = Array.isArray(graphData?.nodes) ? graphData.nodes : [];
    return rows.map((node: Json) => ({
      id: String(node.id),
      name: typeof node.name === "string" ? node.name : "",
    }));
  }, [graphData]);
  const graphEdges = useMemo<GraphEdge[]>(() => {
    const rows = Array.isArray(graphData?.edges) ? graphData.edges : [];
    return rows
      .filter((edge: Json) => edge.id && edge.subject_id && edge.object_id)
      .map((edge: Json) => ({
        id: String(edge.id),
        subject_id: String(edge.subject_id),
        object_id: String(edge.object_id),
        predicate: typeof edge.predicate === "string" ? edge.predicate : "",
      }));
  }, [graphData]);
  const nodeName = new Map(graphNodes.map((node) => [node.id, node.name]));
  const centerName = graph ? (nodeName.get(graph) ?? "") : "";
  const mountCanvas = width > 768 && graphQuery.isSuccess;
  async function save(values: Json) {
    if (!canEdit) return;
    try {
      const value =
        category === "belief"
          ? {
              proposition: values.proposition,
              stance: values.stance,
              attitude: values.attitude || "",
              confidence: values.confidence || "",
            }
          : { text: values.value || "" };
      const fact = {
        predicate: values.predicate || category,
        category,
        object_id: values.object_id || null,
        value,
        calendar: values.calendar || null,
        world_from: values.world_from || null,
        world_to: values.world_to || null,
        chapter_id: values.chapter_id || null,
        secret: !!values.secret,
        source: { kind: "author", note: values.note || "" },
      };
      await adopt(
        scope,
        [{ op: "fact", entity_id: values.subject_id, fact }],
        "维护关系与历史",
      );
      setOpen(false);
      form.resetFields();
      refresh();
      query.refetch();
      message.success("记录已采用");
    } catch (e) {
      message.error((e as Error).message);
    }
  }
  async function move(values: Json) {
    if (!canEdit) return;
    try {
      const old = transfer!;
      const retained = {
        predicate: old.predicate,
        category: "relation",
        object_id: old.object_id,
        value: old.value,
        calendar: old.calendar,
        world_from: old.world_from,
        world_to: values.time,
        supersedes: old.id,
        source: { kind: "author", note: "关闭流转前区间" },
      };
      const next = {
        ...retained,
        world_from: values.time,
        world_to: null,
        supersedes: null,
        source: { kind: "author", note: values.note || "流转" },
      };
      await adopt(
        scope,
        [
          { op: "fact", entity_id: old.subject_id, fact: retained },
          { op: "fact", entity_id: values.owner, fact: next },
        ],
        "物品流转",
      );
      setTransfer(undefined);
      query.refetch();
      refresh();
      message.success("流转与历史已同步");
    } catch (e) {
      message.error((e as Error).message);
    }
  }
  return (
    <>
      <PageTitle
        title="关系、认知与时间"
        note="世界有效时间和系统记录版本分别查询。多重隶属、名义/实际关系分别保留。"
        actions={
          <div>
            <Button
              type="primary"
              className="hit-44"
              icon={<PlusOutlined />}
              disabled={!canEdit}
              onClick={() => setOpen(true)}
            >
              新增记录
            </Button>
            {!canEdit && <p className="perm-note">需要编辑权限</p>}
          </div>
        }
      />
      <p className="scope-note" data-component="scope-line">
        {scopeLine(scope.name, scope.kind, scope.version)}
      </p>
      <Card>
        <Space wrap style={{ marginBottom: 20 }}>
          <Select
            aria-label="记录类别"
            value={category}
            onChange={setCategory}
            style={{ width: 150 }}
            options={[
              ["relation", "关系与组织"],
              ["belief", "角色认知"],
              ["reveal", "读者揭示"],
              ["fact", "世界事实"],
              ["name", "名称与别名"],
              ["plan", "未来规划"],
            ].map(([value, label]) => ({ value, label }))}
          />
          <Input
            placeholder="历法 / 坐标口径"
            style={{ width: 160 }}
            value={calendar}
            onChange={(e) => setCalendar(e.target.value)}
          />
          <Input
            placeholder="故事内时点"
            style={{ width: 160 }}
            value={worldAt}
            onChange={(e) => setWorldAt(e.target.value)}
          />
          <InputNumber
            aria-label="记录截至版本"
            placeholder="当前记录版本"
            min={0}
            max={scope.version}
            value={asOf}
            onChange={(v) => setAsOf(v ?? undefined)}
          />
        </Space>
        {query.isPending && (
          <Skeleton active title={false} paragraph={{ rows: 4 }} />
        )}
        {query.isFetching && query.isSuccess && (
          <p className="perm-note">正在重新读取</p>
        )}
        {query.isError && (
          <Alert
            type="error"
            showIcon
            title={effectDetail(query.error)}
            action={<Button onClick={() => query.refetch()}>重试</Button>}
          />
        )}
        {query.data?.uncertain_time_count > 0 && (
          <Alert
            type="info"
            title={`${query.data?.uncertain_time_count}项历法不明确，未伪造精确时点`}
          />
        )}
        <Table<Json>
          rowKey="id"
          loading={query.isPending}
          dataSource={query.isPending ? undefined : factItems}
          locale={{
            emptyText:
              query.isSuccess && factItems.length === 0 ? (
                <NoData text="没有已加载的关系边" />
              ) : (
                <span />
              ),
          }}
          pagination={{ pageSize: 15 }}
          columns={[
            {
              title: "对象",
              dataIndex: "subject_id",
              render: (v) => (
                <Button type="link" onClick={() => setGraph(v)}>
                  {labels.get(v) || v.slice(0, 8)}
                </Button>
              ),
            },
            { title: "关系/命题", dataIndex: "predicate" },
            {
              title: "关联对象 / 值",
              render: (_, r) =>
                r.object_id
                  ? labels.get(r.object_id) || r.object_id.slice(0, 8)
                  : JSON.stringify(r.value),
            },
            {
              title: "世界有效区间",
              render: (_, r) =>
                r.calendar
                  ? `${r.calendar} [${r.world_from ?? "未知"}, ${r.world_to ?? "持续"})`
                  : "未知 / 未定时",
            },
            { title: "记录版本", dataIndex: "recorded_from" },
            {
              title: "操作",
              render: (_, r) => (
                <Space>
                  {["owns", "custody"].includes(r.predicate) &&
                    r.calendar &&
                    scope.actions.includes("edit") && (
                      <Button type="link" onClick={() => setTransfer(r)}>
                        流转
                      </Button>
                    )}
                  <Button
                    type="link"
                    className="hit-44"
                    disabled={!canEdit}
                    onClick={async () => {
                      if (!canEdit) return;
                      try {
                        await adopt(
                          scope,
                          [
                            {
                              op: "retract",
                              entity_id: r.subject_id,
                              fact_id: r.id,
                            },
                          ],
                          "撤回事实记录",
                        );
                        query.refetch();
                        refresh();
                      } catch (e) {
                        message.error((e as Error).message);
                      }
                    }}
                  >
                    撤回
                  </Button>
                </Space>
              ),
            },
          ]}
        />
      </Card>
      <Modal
        title="维护一项记录"
        open={open}
        width={720}
        onCancel={() => setOpen(false)}
        okButtonProps={{ disabled: !canEdit }}
        onOk={() => form.submit()}
        destroyOnHidden
      >
        <Form form={form} layout="vertical" onFinish={save}>
          <Form.Item
            name="subject_id"
            label="主体"
            rules={[{ required: true }]}
          >
            <ReferenceInput />
          </Form.Item>
          <Form.Item
            name="predicate"
            label="关系/属性"
            rules={[{ required: true }]}
          >
            {category === "relation" ? (
              <Select
                options={defs.data
                  ?.filter((d) => d.spec.relation)
                  .map((d) => ({
                    value: d.key.replace(/^rel:/, ""),
                    label: d.spec.label,
                  }))}
              />
            ) : (
              <Input />
            )}
          </Form.Item>
          {category === "relation" && (
            <Form.Item
              name="object_id"
              label="目标"
              rules={[{ required: true }]}
            >
              <ReferenceInput />
            </Form.Item>
          )}
          {category === "belief" ? (
            <>
              <Form.Item
                name="proposition"
                label="命题"
                rules={[{ required: true }]}
              >
                <Input />
              </Form.Item>
              <Form.Item
                name="stance"
                label="信念状态"
                rules={[{ required: true }]}
              >
                <Select
                  options={[
                    ["knows", "知道"],
                    ["suspects", "怀疑"],
                    ["misbelieves", "误信"],
                    ["unaware", "不知"],
                    ["denies", "否认"],
                  ].map(([value, label]) => ({ value, label }))}
                />
              </Form.Item>
              <Form.Item name="attitude" label="对外态度">
                <Input />
              </Form.Item>
            </>
          ) : (
            <Form.Item name="value" label="说明 / 值">
              <Input.TextArea />
            </Form.Item>
          )}
          <Space align="start">
            <Form.Item name="calendar" label="历法">
              <Input />
            </Form.Item>
            <Form.Item name="world_from" label="有效起点">
              <Input />
            </Form.Item>
            <Form.Item name="world_to" label="有效终点">
              <Input placeholder="不填为持续" />
            </Form.Item>
          </Space>
          <Form.Item name="chapter_id" label="从哪章出现 / 揭示">
            <ReferenceInput />
          </Form.Item>
          <Form.Item name="note" label="来源或作者决定">
            <Input.TextArea />
          </Form.Item>
          <Form.Item name="secret" valuePropName="checked">
            <Checkbox>隐藏关系 / 作者秘密</Checkbox>
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        open={!!transfer}
        title="转移所有权或保管关系"
        onCancel={() => setTransfer(undefined)}
        okButtonProps={{ disabled: !canEdit }}
        onOk={() => transferForm.submit()}
      >
        <Form form={transferForm} layout="vertical" onFinish={move}>
          <Form.Item name="owner" label="新的主体" rules={[{ required: true }]}>
            <ReferenceInput />
          </Form.Item>
          <Form.Item
            name="time"
            label={`生效时点（${transfer?.calendar || ""}）`}
            rules={[{ required: true }]}
          >
            <Input />
          </Form.Item>
          <Form.Item name="note" label="流转事件与来源">
            <Input />
          </Form.Item>
        </Form>
      </Modal>
      {graph && (
        <Card
          title="局部关系图"
          extra={
            <Button className="hit-44" onClick={() => setGraph(undefined)}>
              关闭
            </Button>
          }
        >
          {graphQuery.isPending && (
            <Skeleton active title={false} paragraph={{ rows: 3 }} />
          )}
          {graphQuery.isError && (
            <Alert
              type="error"
              showIcon
              title={effectDetail(graphQuery.error)}
              action={
                <Button onClick={() => graphQuery.refetch()}>重试</Button>
              }
            />
          )}
          {graphQuery.isSuccess && (
            <div className="rel-split">
              <div>
                {centerName && <p>中心 {centerName}</p>}
                {graphData?.truncated === true && (
                  <p>图谱已限定范围，请按节点继续查询；未加载不代表不存在</p>
                )}
                {graphEdges.length === 0 && <p>没有已加载的关系边</p>}
                <table className="plain-table">
                  <thead>
                    <tr>
                      <th>节点</th>
                      <th>位置</th>
                    </tr>
                  </thead>
                  <tbody>
                    {graphNodes.map((node) => (
                      <tr key={node.id}>
                        <td>{node.name}</td>
                        <td>{node.id === graph ? "中心" : "相邻"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <table className="plain-table">
                  <thead>
                    <tr>
                      <th>谓词</th>
                      <th>从</th>
                      <th>到</th>
                    </tr>
                  </thead>
                  <tbody>
                    {graphEdges.map((edge) => (
                      <tr key={edge.id}>
                        <td>{edge.predicate}</td>
                        <td>{nodeName.get(edge.subject_id) || ""}</td>
                        <td>{nodeName.get(edge.object_id) || ""}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {mountCanvas && (
                <Suspense fallback="加载图谱">
                  <div>
                    <Graph nodes={graphNodes} edges={graphEdges} />
                    <p className="rel-caption">
                      图和表是同一批节点。拖动不写回故事关系。
                    </p>
                  </div>
                </Suspense>
              )}
            </div>
          )}
        </Card>
      )}
    </>
  );
}
