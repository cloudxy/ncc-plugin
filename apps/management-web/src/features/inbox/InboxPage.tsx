import { useQuery } from "@tanstack/react-query";
import { App, Button, Card, Col, List, Row, Space } from "antd";
import { api, scoped, type Json } from "../../shared/api";
import { NoData, PageTitle, Status } from "../../shared/components/Feedback";
import { useWorkspace } from "../../shared/WorkspaceContext";

export function InboxPage() {
  const { scope } = useWorkspace(),
    { message } = App.useApp();
  const jobs = useQuery({
    queryKey: ["scope", scope.id, "jobs"],
    queryFn: () => api<Json[]>(scoped(scope.id, "/jobs")),
    refetchInterval: 3000,
  });
  const changes = useQuery({
    queryKey: ["scope", scope.id, "changes"],
    queryFn: () => api<Json[]>(scoped(scope.id, "/changes")),
  });
  const pending = (jobs.data || []).filter((j) =>
    ["qualified", "waiting", "failed"].includes(j.state),
  );
  return (
    <>
      <PageTitle
        title="我的待办"
        note="只汇总需要你选择的结果；内部成功步骤自动继续。"
      />
      <Row gutter={24}>
        <Col xs={24} lg={14}>
          <Card title="创作与任务">
            <List
              dataSource={pending}
              locale={{ emptyText: <NoData text="当前没有需要你决定的任务" /> }}
              renderItem={(job) => (
                <List.Item
                  actions={[
                    job.state === "qualified" ? (
                      <Button
                        type="primary"
                        disabled={!scope.actions.includes("adopt")}
                        onClick={async () => {
                          try {
                            await api(
                              scoped(scope.id, `/jobs/${job.id}/adopt`),
                              "POST",
                            );
                            jobs.refetch();
                            message.success("已采用");
                          } catch (e) {
                            message.error((e as Error).message);
                          }
                        }}
                      >
                        采用
                      </Button>
                    ) : null,
                  ]}
                >
                  <List.Item.Meta
                    title={
                      <Space>
                        {job.payload?.name || job.kind}
                        <Status value={job.state} />
                      </Space>
                    }
                    description={
                      job.result?.error?.detail ||
                      job.result?.auto_hold?.detail ||
                      "查看创作台中的评分、变化和候选，再决定采用或修改。"
                    }
                  />
                </List.Item>
              )}
            />
          </Card>
        </Col>
        <Col xs={24} lg={10}>
          <Card title="资料变更">
            <List
              dataSource={(changes.data || []).filter(
                (x) => x.state !== "applied",
              )}
              locale={{ emptyText: "没有未采用的变更" }}
              renderItem={(change) => (
                <List.Item
                  actions={[
                    <Button
                      type="link"
                      disabled={!scope.actions.includes("adopt")}
                      onClick={async () => {
                        try {
                          await api(
                            scoped(scope.id, `/changes/${change.id}/adopt`),
                            "POST",
                          );
                          changes.refetch();
                          message.success("变更已采用");
                        } catch (e) {
                          message.error((e as Error).message);
                        }
                      }}
                    >
                      预检并采用
                    </Button>,
                  ]}
                >
                  <List.Item.Meta
                    title={change.title}
                    description={<Status value={change.state} />}
                  />
                </List.Item>
              )}
            />
          </Card>
        </Col>
      </Row>
    </>
  );
}
