import { useQuery } from "@tanstack/react-query";
import {
  App,
  Button,
  Card,
  Col,
  Drawer,
  List,
  Row,
  Space,
  Table,
  Tag,
  Typography,
} from "antd";
import { useState } from "react";
import { api, scoped, type Json } from "../../shared/api";
import {
  ErrorPanel,
  NoData,
  PageTitle,
} from "../../shared/components/Feedback";
import { useWorkspace } from "../../shared/WorkspaceContext";
import { EntityDrawer } from "../knowledge/components/EntityDrawer";

export function QualityPage() {
  const { message } = App.useApp();
  const { scope } = useWorkspace(),
    [detail, setDetail] = useState<string>(),
    [report, setReport] = useState<Json>();
  const quality = useQuery({
    queryKey: ["scope", scope.id, "quality"],
    queryFn: () => api<Json>(scoped(scope.id, "/quality")),
  });
  const scores = useQuery({
    queryKey: ["scope", scope.id, "assessments"],
    queryFn: () => api<Json[]>(scoped(scope.id, "/assessments")),
  });
  return (
    <>
      <PageTitle
        title="质量与评分"
        note="每份报告绑定内容与规则版本。作者偏好独立记录，历史分数不会被改成当前新稿的结论。"
      />
      <Row gutter={24}>
        <Col xs={24} xl={9}>
          <Card title="数据问题与待核实">
            <ErrorPanel error={quality.error} />
            <List
              dataSource={quality.data?.items}
              locale={{
                emptyText: <NoData text="本次检查范围内没有待处理问题" />,
              }}
              renderItem={(issue: Json) => (
                <List.Item
                  actions={[
                    <Button
                      type="link"
                      onClick={() => setDetail(issue.entity_id)}
                    >
                      定位
                    </Button>,
                  ]}
                >
                  <List.Item.Meta
                    title={issue.detail}
                    description={<Tag>{issue.kind}</Tag>}
                  />
                </List.Item>
              )}
            />
            <p className="muted">
              覆盖口径：{quality.data?.coverage || "等待检查"}
              。覆盖不足时不会直接判定伏笔遗忘。
            </p>
          </Card>
        </Col>
        <Col xs={24} xl={15}>
          <Card title="AI内容评分">
            <ErrorPanel error={scores.error} />
            <Table
              rowKey="id"
              dataSource={scores.data}
              loading={scores.isPending}
              pagination={{ pageSize: 12 }}
              columns={[
                { title: "类型", dataIndex: "scheme" },
                {
                  title: "总分",
                  dataIndex: "score",
                  render: (v) => (
                    <b className="score-number">{v ?? "待评分"}</b>
                  ),
                },
                {
                  title: "结论",
                  dataIndex: "verdict",
                  render: (v) => (
                    <Tag color={v === "qualified" ? "green" : "orange"}>
                      {(
                        {
                          qualified: "达标",
                          revise: "需修改",
                          restructure: "需重构",
                          blocked: "硬伤阻断",
                          incomplete: "依据不足",
                        } as Json
                      )[v] || v}
                    </Tag>
                  ),
                },
                {
                  title: "有效性",
                  dataIndex: "fresh",
                  render: (v) => <Tag>{v ? "当前依据" : "历史 / 待复评"}</Tag>,
                },
                {
                  title: "操作",
                  render: (_, r) => (
                    <Button type="link" onClick={() => setReport(r)}>
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
        width={760}
        open={!!report}
        title="评分、依据与反馈"
        onClose={() => setReport(undefined)}
      >
        <Typography.Paragraph>
          {report?.report?.report?.summary}
        </Typography.Paragraph>
        <Space wrap>
          {[
            ["satisfied", "满意"],
            ["usable", "可用"],
            ["dislike", "不喜欢"],
            ["prefer_other", "更喜欢其他版本"],
          ].map(([choice, label]) => (
            <Button
              key={choice}
              onClick={async () => {
                try {
                  await api(
                    scoped(scope.id, `/assessments/${report?.id}/feedback`),
                    "POST",
                    { choice, note: "" },
                  );
                  message.success("偏好已单独记录，原分数保留");
                } catch (e) {
                  message.error((e as Error).message);
                }
              }}
            >
              {label}
            </Button>
          ))}
        </Space>
        <pre className="json-block">{JSON.stringify(report, null, 2)}</pre>
      </Drawer>
    </>
  );
}
