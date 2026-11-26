import { useQuery } from "@tanstack/react-query";
import {
  Alert,
  App,
  Button,
  Card,
  Col,
  Drawer,
  Input,
  List,
  Row,
  Space,
  Table,
  Tag,
  Typography,
} from "antd";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, scoped, type Json } from "../../shared/api";
import {
  ErrorPanel,
  NoData,
  PageTitle,
} from "../../shared/components/Feedback";
import { queryKeys } from "../../shared/queryKeys";
import { setLastEditedChapter } from "../../shared/studioApi";
import { useWorkspace } from "../../shared/WorkspaceContext";
import { EntityDrawer } from "../knowledge/components/EntityDrawer";

const ISSUE_KIND_LABELS: Record<string, string> = {
  duplicate_candidate: "疑似同名候选",
  payoff_evidence: "伏笔回收缺少兑现章节",
  insufficient_coverage: "观察章节覆盖不足",
  unverified_attribution: "语录出处尚未核实",
};

const SCHEME_LABELS: Record<string, string> = {
  P1: "P1 正文章节",
  P2: "P2 大纲细纲",
  P3: "P3 人物设定",
  P4: "P4 资料来源",
  P5: "P5 修改复评",
};

const VERDICT_LABELS: Record<string, { label: string; color: string }> = {
  qualified: { label: "达标", color: "success" },
  review: { label: "待人工裁决", color: "processing" },
  revise: { label: "需修改", color: "warning" },
  restructure: { label: "需重构", color: "warning" },
  blocked: { label: "硬伤阻断", color: "error" },
  incomplete: { label: "依据不足", color: "default" },
};

function extractDimensions(rawReport: Json | undefined): {
  key: string;
  score: string;
  reason: string;
  evidence: string;
}[] {
  const inner = rawReport?.report?.report || rawReport?.report || {};
  const dims = inner.dimensions;
  if (!dims || typeof dims !== "object") return [];
  if (Array.isArray(dims)) {
    return dims.map((d: Json, idx: number) => ({
      key: String(d?.name || d?.dimension || `维度 ${idx + 1}`),
      score: d?.score != null ? String(d.score) : "-",
      reason: String(d?.reason || d?.comment || d?.detail || ""),
      evidence: Array.isArray(d?.evidence)
        ? d.evidence.join("；")
        : String(d?.evidence || d?.quote || ""),
    }));
  }
  return Object.entries(dims).map(([name, val]: [string, any]) => {
    if (typeof val === "number" || typeof val === "string") {
      return { key: name, score: String(val), reason: "", evidence: "" };
    }
    return {
      key: String(val?.label || name),
      score: val?.score != null ? String(val.score) : "-",
      reason: String(val?.reason || val?.comment || val?.detail || ""),
      evidence: Array.isArray(val?.evidence)
        ? val.evidence.join("；")
        : String(val?.evidence || val?.quote || ""),
    };
  });
}

function extractSuggestions(rawReport: Json | undefined): string[] {
  const inner = rawReport?.report?.report || rawReport?.report || {};
  if (!Array.isArray(inner.suggestions)) return [];
  return inner.suggestions
    .map((item: unknown) =>
      typeof item === "string"
        ? item
        : typeof (item as Json)?.detail === "string"
          ? String((item as Json).detail)
          : "",
    )
    .filter(Boolean);
}

export function QualityPage() {
  const { message } = App.useApp();
  const navigate = useNavigate();
  const { scope } = useWorkspace(),
    [detail, setDetail] = useState<string>(),
    [report, setReport] = useState<Json>(),
    [feedbackNote, setFeedbackNote] = useState(""),
    [submittingFeedback, setSubmittingFeedback] = useState("");

  const quality = useQuery({
    queryKey: queryKeys.quality(scope.id),
    queryFn: () => api<Json>(scoped(scope.id, "/quality")),
  });
  const scores = useQuery({
    queryKey: queryKeys.assessments(scope.id),
    queryFn: () => api<Json[]>(scoped(scope.id, "/assessments")),
  });

  const reportInner = report?.report?.report || report?.report || {};
  const dimensionRows = extractDimensions(report);
  const suggestionRows = extractSuggestions(report);

  return (
    <>
      <PageTitle
        title="质量与评分"
        note="每份报告绑定内容与规则版本。作者偏好独立记录，历史分数不会被改成当前新稿的结论。"
      />
      <Row gutter={[24, 24]}>
        <Col xs={24} xl={9}>
          <Card title="数据问题与待核实">
            <ErrorPanel error={quality.error} retry={() => quality.refetch()} />
            <List
              dataSource={quality.data?.items}
              locale={{
                emptyText: <NoData text="本次检查范围内没有待处理问题" />,
              }}
              renderItem={(issue: Json) => (
                <List.Item
                  actions={[
                    <Button
                      key="locate"
                      type="link"
                      onClick={() => setDetail(issue.entity_id)}
                    >
                      定位对象
                    </Button>,
                  ]}
                >
                  <List.Item.Meta
                    title={issue.detail}
                    description={
                      <Tag>{ISSUE_KIND_LABELS[issue.kind] || issue.kind}</Tag>
                    }
                  />
                </List.Item>
              )}
            />
            <p className="muted">
              覆盖口径：{quality.data?.coverage || "等待检查"}
              {typeof quality.data?.scanned === "number"
                ? `（已扫描 ${quality.data.scanned} 条）`
                : ""}
              。覆盖不足时不会直接判定伏笔遗忘。
            </p>
          </Card>
        </Col>
        <Col xs={24} xl={15}>
          <Card title="AI内容评分">
            <ErrorPanel error={scores.error} retry={() => scores.refetch()} />
            <Table<Json>
              rowKey="id"
              dataSource={scores.data}
              loading={scores.isPending}
              locale={{
                emptyText: <NoData text="当前空间还没有 AI 内容评分报告" />,
              }}
              pagination={{ pageSize: 12 }}
              columns={[
                {
                  title: "评估对象",
                  render: (_, r) => {
                    const name = r.entity_name || "未绑定正式条目";
                    const isChapter =
                      r.entity_kind === "chapter" ||
                      r.entity_kind === "章节" ||
                      (!r.entity_kind && r.scheme === "P1");
                    if (!r.entity_id) {
                      return <span>{name}</span>;
                    }
                    return (
                      <Space wrap size={4}>
                        <b>{name}</b>
                        {r.entity_kind && <Tag>{r.entity_kind}</Tag>}
                        {isChapter ? (
                          <Button
                            size="small"
                            type="link"
                            onClick={() => {
                              setLastEditedChapter(
                                scope.id,
                                String(r.entity_id),
                              );
                              navigate(
                                `/work?scope=${encodeURIComponent(scope.id)}&entity=${encodeURIComponent(String(r.entity_id))}`,
                              );
                            }}
                          >
                            去创作台
                          </Button>
                        ) : (
                          <Button
                            size="small"
                            type="link"
                            onClick={() => setDetail(String(r.entity_id))}
                          >
                            查看卡片
                          </Button>
                        )}
                      </Space>
                    );
                  },
                },
                {
                  title: "评分方案",
                  dataIndex: "scheme",
                  width: 130,
                  render: (v: string) => SCHEME_LABELS[v] || v,
                },
                {
                  title: "总分",
                  dataIndex: "score",
                  width: 90,
                  render: (v) => (
                    <b className="score-number">{v ?? "待评分"}</b>
                  ),
                },
                {
                  title: "结论",
                  dataIndex: "verdict",
                  width: 115,
                  render: (v: string) => {
                    const meta = VERDICT_LABELS[v] || {
                      label: v || "-",
                      color: "default",
                    };
                    return <Tag color={meta.color}>{meta.label}</Tag>;
                  },
                },
                {
                  title: "时效与时间",
                  width: 170,
                  render: (_, r) => (
                    <Space orientation="vertical" size={2}>
                      <Tag color={r.fresh ? "success" : "default"}>
                        {r.fresh ? "当前有效依据" : "历史 / 待复评"}
                      </Tag>
                      {r.created_at && (
                        <small style={{ color: "#3e5147" }}>
                          {new Date(r.created_at).toLocaleString()}
                        </small>
                      )}
                    </Space>
                  ),
                },
                {
                  title: "操作",
                  width: 110,
                  render: (_, r) => (
                    <Button
                      type="link"
                      onClick={() => {
                        setReport(r);
                        setFeedbackNote("");
                      }}
                    >
                      分项与证据
                    </Button>
                  ),
                },
              ]}
            />
          </Card>
        </Col>
      </Row>
      <EntityDrawer id={detail} onClose={() => setDetail(undefined)} />
      <Drawer
        size="large"
        open={!!report}
        title={
          report?.entity_name
            ? `评分、依据与反馈 · ${report.entity_name}`
            : "评分、依据与反馈"
        }
        onClose={() => setReport(undefined)}
      >
        {report && (
          <Space orientation="vertical" size={16} style={{ width: "100%" }}>
            <Space wrap>
              <Tag>{SCHEME_LABELS[report.scheme] || report.scheme}</Tag>
              <Tag color={VERDICT_LABELS[report.verdict]?.color || "default"}>
                结论：{VERDICT_LABELS[report.verdict]?.label || report.verdict}
              </Tag>
              <Tag color={report.fresh ? "success" : "default"}>
                {report.fresh ? "对应最新正文版本" : "正文已变动 · 历史快照"}
              </Tag>
              {reportInner.hard && (
                <Tag color={reportInner.hard === "pass" ? "success" : "error"}>
                  硬伤门禁：
                  {reportInner.hard === "pass"
                    ? "通过"
                    : String(reportInner.hard)}
                </Tag>
              )}
            </Space>

            {reportInner.summary ? (
              <Alert
                type="info"
                showIcon
                title="总体审评结论"
                description={String(reportInner.summary)}
              />
            ) : (
              <Typography.Text type="secondary">
                该记录未附带文字总评摘要。
              </Typography.Text>
            )}

            <div>
              <Typography.Title level={5} style={{ marginTop: 0 }}>
                分项维度得分与原文证据
              </Typography.Title>
              {dimensionRows.length === 0 ? (
                <Typography.Text type="secondary">
                  本次评估未拆分细分维度条目。
                </Typography.Text>
              ) : (
                <Table
                  size="small"
                  rowKey="key"
                  pagination={false}
                  dataSource={dimensionRows}
                  columns={[
                    { title: "维度", dataIndex: "key", width: 130 },
                    {
                      title: "得分",
                      dataIndex: "score",
                      width: 80,
                      render: (v) => <b>{v}</b>,
                    },
                    {
                      title: "判定理由与原文证据",
                      render: (_, d) => (
                        <div>
                          {d.reason && <div>{d.reason}</div>}
                          {d.evidence && (
                            <div style={{ color: "#3e5147", marginTop: 4 }}>
                              原文依据：「{d.evidence}」
                            </div>
                          )}
                          {!d.reason && !d.evidence && "-"}
                        </div>
                      ),
                    },
                  ]}
                />
              )}
            </div>

            {suggestionRows.length > 0 && (
              <div>
                <Typography.Title level={5} style={{ marginTop: 0 }}>
                  可执行修改建议
                </Typography.Title>
                <ul style={{ paddingLeft: 20, margin: 0 }}>
                  {suggestionRows.map((item, index) => (
                    <li key={index} style={{ marginBottom: 6 }}>
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <Card size="small" title="记录作者偏好反馈（不影响历史评分）">
              <Input.TextArea
                aria-label="反馈备注"
                rows={2}
                maxLength={4000}
                style={{ marginBottom: 10 }}
                placeholder="可选：写下你对这一版评分或正文的判断（例如：节奏其实符合铺垫预期、人物口吻抓得准等）"
                value={feedbackNote}
                onChange={(e) => setFeedbackNote(e.target.value)}
              />
              <Space wrap>
                {[
                  ["satisfied", "满意"],
                  ["usable", "可用"],
                  ["dislike", "不喜欢"],
                  ["prefer_other", "更喜欢其他版本"],
                ].map(([choice, label]) => (
                  <Button
                    key={choice}
                    loading={submittingFeedback === choice}
                    onClick={async () => {
                      setSubmittingFeedback(choice);
                      try {
                        await api(
                          scoped(
                            scope.id,
                            `/assessments/${report.id}/feedback`,
                          ),
                          "POST",
                          { choice, note: feedbackNote.trim() },
                        );
                        message.success("偏好与备注已单独记录，原分数保留");
                      } catch (e) {
                        message.error((e as Error).message);
                      } finally {
                        setSubmittingFeedback("");
                      }
                    }}
                  >
                    {label}
                  </Button>
                ))}
              </Space>
            </Card>

            <details>
              <summary>查看完整原始评估 JSON</summary>
              <pre className="json-block">
                {JSON.stringify(report, null, 2)}
              </pre>
            </details>
          </Space>
        )}
      </Drawer>
    </>
  );
}
