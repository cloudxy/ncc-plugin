import { useQuery } from "@tanstack/react-query";
import { App, Button, Card, Drawer, Space, Table } from "antd";
import { useState } from "react";
import { api, scoped, type Json } from "../../shared/api";
import {
  ErrorPanel,
  PageTitle,
  Status,
} from "../../shared/components/Feedback";
import { stages } from "../../shared/jobStages";
import { useWorkspace } from "../../shared/WorkspaceContext";

export function JobsPage() {
  const { scope } = useWorkspace(),
    { message } = App.useApp(),
    [selected, setSelected] = useState<Json>();
  const jobs = useQuery({
    queryKey: ["scope", scope.id, "jobs"],
    queryFn: () => api<Json[]>(scoped(scope.id, "/jobs")),
    refetchInterval: 2500,
  });
  async function act(job: Json, action: string) {
    try {
      await api(
        scoped(
          scope.id,
          `/jobs/${job.id}/${action === "cancel" ? "cancel" : "intervene"}`,
        ),
        "POST",
        action === "cancel" ? {} : { action },
      );
      jobs.refetch();
    } catch (e) {
      message.error((e as Error).message);
    }
  }
  return (
    <>
      <PageTitle
        title="任务中心"
        note="进度与回执持久保存。取消会停止后续处理，已提交批次保留记录。"
      />
      <ErrorPanel error={jobs.error} retry={() => jobs.refetch()} />
      <Card>
        <Table
          rowKey="id"
          loading={jobs.isPending}
          dataSource={jobs.data}
          pagination={{ pageSize: 15 }}
          columns={[
            {
              title: "任务",
              render: (_, r) =>
                r.payload?.name ||
                (
                  {
                    creation: "创作任务",
                    index: "索引更新",
                    import: "批量导入",
                    export: "数据导出",
                  } as Json
                )[r.kind] ||
                r.kind,
            },
            {
              title: "状态",
              dataIndex: "state",
              render: (x) => <Status value={x} />,
            },
            {
              title: "进度",
              render: (_, r) =>
                r.progress?.total
                  ? `${r.progress.committed} / ${r.progress.total}`
                  : stages[r.progress?.stage] || "—",
            },
            {
              title: "建立时间",
              dataIndex: "created_at",
              render: (x) => new Date(x).toLocaleString(),
            },
            {
              title: "操作",
              render: (_, r) => (
                <Space>
                  <Button type="link" onClick={() => setSelected(r)}>
                    详情
                  </Button>
                  {["running", "queued"].includes(r.state) && (
                    <Button type="link" onClick={() => act(r, "cancel")}>
                      取消
                    </Button>
                  )}
                  {r.kind === "creation" &&
                    ["failed", "paused", "waiting"].includes(r.state) && (
                      <Button type="link" onClick={() => act(r, "resume")}>
                        恢复
                      </Button>
                    )}
                </Space>
              ),
            },
          ]}
        />
      </Card>
      <Drawer
        title="任务详情与回执"
        open={!!selected}
        onClose={() => setSelected(undefined)}
        width={760}
      >
        <pre className="json-block">{JSON.stringify(selected, null, 2)}</pre>
      </Drawer>
    </>
  );
}
