import {
  CheckOutlined,
  EditOutlined,
  PauseOutlined,
  StarOutlined,
} from "@ant-design/icons";
import {
  Alert,
  Button,
  Card,
  Drawer,
  Progress,
  Select,
  Space,
  Statistic,
  Table,
  Tag,
  Typography,
} from "antd";
import { useState } from "react";
import { api, scoped, type Json } from "../../../shared/api";
import { NoData, Status } from "../../../shared/components/Feedback";
import { TextEditor } from "../../../shared/components/TextEditor";
import { useWorkspace } from "../../../shared/WorkspaceContext";

import { stages } from "../../../shared/jobStages";
import { useCreationPolicy } from "../../../shared/useCreationPolicy";

export function ScoreCard({
  job,
  onAdopt,
  onEdit,
  onRefresh,
}: {
  job?: Json;
  onAdopt: () => void;
  onEdit: (text: string) => void;
  onRefresh: () => void;
}) {
  const [details, setDetails] = useState(false),
    { scope } = useWorkspace();
  const policy = useCreationPolicy();
  const candidates = job?.result?.candidates || [],
    selected = job?.result?.selected ?? candidates.length - 1,
    candidate = candidates[selected];
  const evaluation = candidate?.evaluation,
    report = evaluation?.report;
  const running = job?.state === "running" || job?.state === "queued";
  return (
    <Card
      className="score-card"
      title={
        <Space>
          <StarOutlined />
          质量与进度
        </Space>
      }
      extra={job && <Status value={job.state} />}
    >
      {!job ? (
        <NoData text="生成后会在这里显示评分与依据" />
      ) : (
        <>
          <Typography.Text type="secondary">
            {stages[job.progress?.stage] || "任务处理"}
          </Typography.Text>
          {running && (
            <Progress
              percent={Math.min(
                90,
                15 + Object.keys(stages).indexOf(job.progress?.stage) * 12,
              )}
              status="active"
              showInfo={false}
            />
          )}
          {evaluation ? (
            <>
              <Statistic
                title="AI评估 · 100分制"
                value={evaluation.score ?? "待评分"}
                precision={evaluation.score ? 1 : undefined}
                styles={{
                  content: {
                    color:
                      evaluation.verdict === "qualified"
                        ? "#245d4d"
                        : "#a97424",
                    fontSize: 46,
                  },
                }}
              />
              <Space wrap>
                <Tag color={report?.hard === "pass" ? "green" : "orange"}>
                  硬伤：{report?.hard === "pass" ? "通过" : "待处理"}
                </Tag>
                <Tag>
                  自动修订 {job.progress?.revisions || 0} /{" "}
                  {job.payload?.max_revisions ?? 2}
                </Tag>
              </Space>
              <Typography.Paragraph className="score-summary">
                {report?.summary || evaluation.errors?.join("；")}
              </Typography.Paragraph>
              {report?.suggestions?.slice(0, 3).map((s: string, i: number) => (
                <p className="suggestion" key={i}>
                  <b>{i + 1}</b>
                  {s}
                </p>
              ))}
              <Button type="link" onClick={() => setDetails(true)}>
                查看分项、依据与候选
              </Button>
            </>
          ) : (
            <p className="muted">
              检查与评分完成后显示结果。分数与具体内容版本绑定。
            </p>
          )}
          {job.result?.error && (
            <Alert type="warning" showIcon title={job.result.error.detail} />
          )}
          {job.result?.auto_hold && (
            <Alert type="info" title={job.result.auto_hold.detail} />
          )}
          {job.result?.plan_evaluation && !job.result?.plan_valid && (
            <Alert
              type="warning"
              title="场景计划尚未达标"
              description={
                job.result.plan_evaluation.report?.summary ||
                "请查看任务详情并选择修改方向"
              }
            />
          )}
          {candidate && job.payload?.mode !== "assess" && (
            <Space
              orientation="vertical"
              style={{ width: "100%", marginTop: 20 }}
            >
              <Button
                type="primary"
                block
                icon={<CheckOutlined />}
                onClick={onAdopt}
                disabled={
                  !["qualified", "waiting"].includes(job.state) ||
                  ["blocked", "incomplete"].includes(evaluation?.verdict) ||
                  !scope.actions.includes("adopt") ||
                  candidate?.disputed
                }
              >
                采用当前候选
              </Button>
              <Button
                block
                icon={<EditOutlined />}
                onClick={() => onEdit(candidate.text)}
              >
                放入编辑器继续修改
              </Button>
            </Space>
          )}
          {running && (
            <Button
              block
              style={{ marginTop: 12 }}
              icon={<PauseOutlined />}
              onClick={async () => {
                await api(
                  scoped(scope.id, `/jobs/${job.id}/intervene`),
                  "POST",
                  { action: "pause" },
                );
                onRefresh();
              }}
            >
              暂停并接管
            </Button>
          )}
          <div className="score-foot">
            已使用 {job.progress?.tokens || 0} tokens ·{" "}
            {job.progress?.usage_kind === "conservative_estimate"
              ? "预算估算"
              : "服务端用量记录"}
          </div>
        </>
      )}
      <Drawer
        title="评分依据与候选比较"
        width={720}
        open={details}
        onClose={() => setDetails(false)}
      >
        {job && (
          <Select
            style={{ width: "100%", marginBottom: 20 }}
            value={selected}
            options={candidates.map((c: Json, i: number) => ({
              value: i,
              label: `版本 ${i + 1} · ${c.evaluation?.score ?? "待评分"}分`,
            }))}
            onChange={async (value) => {
              await api(scoped(scope.id, `/jobs/${job.id}/intervene`), "POST", {
                action: "choose",
                candidate: value,
              });
              onRefresh();
            }}
          />
        )}
        <Table
          size="small"
          pagination={false}
          rowKey="key"
          columns={[
            { title: "维度", dataIndex: "label" },
            { title: "分数", dataIndex: "score" },
            { title: "依据", dataIndex: "reason" },
            {
              title: "原文",
              dataIndex: "evidence",
              render: (x: string[]) => x?.join(" / "),
            },
          ]}
          dataSource={Object.entries(report?.dimensions || {}).map(
            ([key, value]) => ({
              key,
              label:
                policy.data?.profiles[
                  candidate?.scheme || job?.payload?.scheme
                ]?.find((x: Json) => x.key === key)?.label || key,
              ...(value as Json),
            }),
          )}
        />
        {candidate?.revision_evaluation && (
          <Alert
            type="info"
            title={`修订执行质量 P5：${candidate.revision_evaluation.score ?? "依据不足"}分`}
            description={candidate.revision_evaluation.report?.summary}
          />
        )}
        {candidate?.second_evaluation && (
          <Alert
            type={candidate.disputed ? "warning" : "info"}
            title={`第二评价：${candidate.second_evaluation.score ?? "依据不足"}分${candidate.disputed ? " · 存在分歧，需复核" : ""}`}
          />
        )}
        {candidate && (
          <>
            <Typography.Title level={5}>此版本内容</Typography.Title>
            <TextEditor value={candidate.text} readOnly height={480} />
          </>
        )}
      </Drawer>
    </Card>
  );
}
