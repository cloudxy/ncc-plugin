import React, { useEffect, useState, useRef, lazy, Suspense } from "react";
import { createRoot } from "react-dom/client";
import {
  App as AntApp,
  Button,
  ConfigProvider,
  Form,
  Input,
  Layout,
  Menu,
  Modal,
  Select,
  Space,
  Spin,
  Tag,
  Typography,
} from "antd";
import zhCN from "antd/locale/zh_CN";
import {
  BookOutlined,
  EditOutlined,
  InboxOutlined,
  DatabaseOutlined,
  BranchesOutlined,
  SettingOutlined,
  LogoutOutlined,
  PlusOutlined,
  ClockCircleOutlined,
  FileSearchOutlined,
  SafetyCertificateOutlined,
  CloudServerOutlined,
  ImportOutlined,
  StarOutlined,
  EnvironmentOutlined,
  HistoryOutlined,
} from "@ant-design/icons";
import {
  QueryClient,
  QueryClientProvider,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import {
  BrowserRouter,
  Route,
  Routes,
  useLocation,
  useNavigate,
} from "react-router-dom";
import { api, scoped, setCSRF, type Json, type Scope } from "./api";
import { Workspace } from "./context";
import { ErrorPanel } from "./common";
const CreativePage = lazy(() =>
  import("./creative").then((x) => ({ default: x.CreativePage })),
);
const InboxPage = lazy(() =>
  import("./creative").then((x) => ({ default: x.InboxPage })),
);
const JobsPage = lazy(() =>
  import("./creative").then((x) => ({ default: x.JobsPage })),
);
const MaterialsPage = lazy(() =>
  import("./materials").then((x) => ({ default: x.MaterialsPage })),
);
const DefinitionsPage = lazy(() =>
  import("./materials").then((x) => ({ default: x.DefinitionsPage })),
);
const RelationsPage = lazy(() =>
  import("./materials").then((x) => ({ default: x.RelationsPage })),
);
const MapPage = lazy(() =>
  import("./materials").then((x) => ({ default: x.MapPage })),
);
const ExchangePage = lazy(() =>
  import("./management").then((x) => ({ default: x.ExchangePage })),
);
const QualityPage = lazy(() =>
  import("./management").then((x) => ({ default: x.QualityPage })),
);
const AdminPage = lazy(() =>
  import("./management").then((x) => ({ default: x.AdminPage })),
);
const MaintenancePage = lazy(() =>
  import("./maintenance").then((x) => ({ default: x.MaintenancePage })),
);
import "./style.css";

const client = new QueryClient({
  defaultOptions: {
    queries: {
      retry: (count, error: any) =>
        error?.status !== 401 && error?.status !== 403 && count < 1,
      staleTime: 1500,
    },
    mutations: { retry: false },
  },
});

function LoginPage({ done }: { done: () => void }) {
  const [busy, setBusy] = useState(false),
    [error, setError] = useState<unknown>();
  return (
    <div className="login-shell">
      <div className="login-intro">
        <div className="brand-mark">N</div>
        <h1>
          让故事生长。
          <br />
          把复杂留给流程。
        </h1>
        <p>Novel Create Center · 私有创作与知识工作台</p>
        <div className="login-lines">
          <span>创作与修改</span>
          <span>世界与人物</span>
          <span>质量与连续性</span>
        </div>
      </div>
      <div className="login-form">
        <Typography.Title level={2}>进入创作空间</Typography.Title>
        <Typography.Paragraph type="secondary">
          使用本机管理员建立的账号登录。
        </Typography.Paragraph>
        <ErrorPanel error={error} />
        <Form
          layout="vertical"
          onFinish={async (values) => {
            setBusy(true);
            setError(undefined);
            try {
              const user = await api<Json>("/auth/login", "POST", values);
              setCSRF(user.csrf);
              done();
            } catch (e) {
              setError(e);
            } finally {
              setBusy(false);
            }
          }}
        >
          <Form.Item name="username" label="账号" rules={[{ required: true }]}>
            <Input autoComplete="username" size="large" />
          </Form.Item>
          <Form.Item name="password" label="密码" rules={[{ required: true }]}>
            <Input.Password autoComplete="current-password" size="large" />
          </Form.Item>
          <Button
            type="primary"
            htmlType="submit"
            loading={busy}
            block
            size="large"
          >
            登录
          </Button>
        </Form>
        <p className="muted">
          首次使用请在终端执行 ncc-data create-user。服务没有默认密码。
        </p>
      </div>
    </div>
  );
}

function Shell() {
  const cache = useQueryClient(),
    nav = useNavigate(),
    location = useLocation(),
    { message, modal } = AntApp.useApp();
  const [authenticated, setAuthenticated] = useState(true),
    [scopeId, setScopeId] = useState(""),
    [dirty, setDirty] = useState(false),
    [newScope, setNewScope] = useState(false),
    [accessEpoch, setAccessEpoch] = useState(0);
  const [form] = Form.useForm();
  const me = useQuery({
    queryKey: ["me"],
    queryFn: () => api<Json>("/me"),
    enabled: authenticated,
    retry: false,
  });
  const scopes = useQuery({
    queryKey: ["scopes", me.data?.id],
    queryFn: () => api<Scope[]>("/scopes"),
    enabled: !!me.data && authenticated,
  });
  const scope = scopeId
    ? scopes.data?.find((x) => x.id === scopeId)
    : scopes.data?.[0];
  const accessStamp = useRef(""),
    activeScope = useRef("");
  activeScope.current = scope?.id || "";
  function resetAccess(sid: string) {
    cache.removeQueries({ queryKey: ["scope", sid] });
    cache.invalidateQueries({ queryKey: ["scopes"] });
    if (activeScope.current === sid) {
      setDirty(false);
      setAccessEpoch((x) => x + 1);
    }
  }
  const currentStamp = scope
    ? scope.id + ":" + scope.actions.slice().sort().join(":")
    : "";
  useEffect(() => {
    if (
      scope &&
      accessStamp.current.startsWith(scope.id + ":") &&
      accessStamp.current !== currentStamp
    )
      resetAccess(scope.id);
    accessStamp.current = currentStamp;
  }, [currentStamp]);
  function refresh() {
    cache.invalidateQueries({ queryKey: ["scope", scope?.id] });
    cache.invalidateQueries({ queryKey: ["scopes"] });
  }
  useEffect(() => {
    if (me.data) setCSRF(me.data.csrf);
  }, [me.data]);
  useEffect(() => {
    const expire = () => {
      setAuthenticated(false);
      setCSRF("");
      cache.clear();
    };
    window.addEventListener("ncc-auth-expired", expire);
    return () => window.removeEventListener("ncc-auth-expired", expire);
  }, [cache]);
  useEffect(() => {
    const before = (event: BeforeUnloadEvent) => {
      if (dirty) {
        event.preventDefault();
        event.returnValue = "";
      }
    };
    window.addEventListener("beforeunload", before);
    return () => window.removeEventListener("beforeunload", before);
  }, [dirty]);
  useEffect(() => {
    if (!scope) return;
    const events = new EventSource(`/api/v1/scopes/${scope.id}/events`);
    events.addEventListener("invalidate", () => refresh());
    events.addEventListener("permissions", (event) => {
      if (activeScope.current !== scope.id) return;
      const stamp =
        scope.id +
        ":" +
        JSON.parse((event as MessageEvent).data)
          .actions.slice()
          .sort()
          .join(":");
      if (accessStamp.current !== stamp) {
        accessStamp.current = stamp;
        resetAccess(scope.id);
      }
    });
    events.addEventListener("access_revoked", () => resetAccess(scope.id));
    events.onerror = () => {
      api<Scope>(scoped(scope.id, ""))
        .then((current) => {
          if (activeScope.current !== scope.id) return;
          const stamp =
            scope.id + ":" + current.actions.slice().sort().join(":");
          if (stamp !== accessStamp.current) {
            accessStamp.current = stamp;
            resetAccess(scope.id);
          }
        })
        .catch((error) => {
          if ([401, 403, 404].includes(error.status)) resetAccess(scope.id);
        });
    };
    return () => events.close();
  }, [scope?.id]);
  function navigate(key: string) {
    if (dirty) {
      modal.confirm({
        title: "保留当前未保存内容？",
        content: "离开前请保存修改。选择离开会放弃当前编辑。",
        okText: "离开",
        cancelText: "继续编辑",
        onOk: () => {
          setDirty(false);
          nav(key);
        },
      });
    } else nav(key);
  }
  if (!authenticated || me.error)
    return (
      <LoginPage
        done={() => {
          setAuthenticated(true);
          cache.clear();
          me.refetch();
        }}
      />
    );
  if (me.isPending || scopes.isPending)
    return (
      <div className="fullscreen">
        <Spin description="正在打开私有工作台" />
      </div>
    );
  const advanced = [
    ["/admin/maintenance", "身份与历史维护", <HistoryOutlined />],
    ["/admin/definitions", "定义中心", <DatabaseOutlined />],
    ["/admin/relations", "关系与时间", <BranchesOutlined />],
    ["/admin/maps", "地图与地点", <EnvironmentOutlined />],
    ["/admin/quality", "质量与评分", <StarOutlined />],
    ["/admin/exchange", "导入与导出", <ImportOutlined />],
    ["/admin/jobs", "任务中心", <ClockCircleOutlined />],
    ["/admin/audit", "操作审计", <SafetyCertificateOutlined />],
    ["/admin/settings", "成员与设置", <SettingOutlined />],
    ["/admin/operations", "运行管理", <CloudServerOutlined />],
  ];
  return (
    <Layout className="app-layout">
      <Layout.Sider width={228} theme="light" className="sidebar">
        <div className="brand">
          <div className="brand-mark small">N</div>
          <div>
            <b>NCC</b>
            <small>创作工作台</small>
          </div>
        </div>
        <Menu
          mode="inline"
          selectedKeys={[location.pathname]}
          onClick={({ key }) => navigate(key)}
          items={[
            { key: "/work", icon: <EditOutlined />, label: "创作台" },
            { key: "/materials", icon: <BookOutlined />, label: "作品资料" },
            { key: "/inbox", icon: <InboxOutlined />, label: "我的待办" },
            { type: "divider" },
            {
              key: "advanced",
              label: "高级管理",
              children: advanced.map(([key, label, icon]) => ({
                key: String(key),
                label,
                icon,
              })),
            },
          ]}
        />
        <div className="sidebar-footer">
          <span className="live-dot" />
          私有资料空间 <Tag bordered={false}>v4.0</Tag>
          <small>创作、事实与修改都有来处。</small>
        </div>
      </Layout.Sider>
      <Layout>
        <Layout.Header className="topbar">
          <Space>
            <Select
              aria-label="当前作品或资料库"
              value={scope?.id}
              style={{ width: 240 }}
              options={scopes.data?.map((s) => ({
                value: s.id,
                label: s.name,
              }))}
              onChange={(value) => {
                if (dirty) {
                  modal.confirm({
                    title: "切换范围将离开当前编辑",
                    onOk: () => {
                      setDirty(false);
                      setScopeId(value);
                    },
                  });
                } else setScopeId(value);
              }}
            />
            <Button
              icon={<PlusOutlined />}
              onClick={() => setNewScope(true)}
              aria-label="新建作品或资料库"
            />
            {scope && (
              <Tag>
                {scope.kind === "branch" ? "IF分支" : "当前采用版"} ·{" "}
                {scope.version}
              </Tag>
            )}
          </Space>
          <Space>
            <Typography.Text type="secondary">
              {me.data?.username}
            </Typography.Text>
            <Button
              type="text"
              icon={<LogoutOutlined />}
              onClick={async () => {
                await api("/auth/logout", "POST");
                setAuthenticated(false);
                cache.clear();
              }}
            >
              退出
            </Button>
          </Space>
        </Layout.Header>
        <Layout.Content className="content">
          <ErrorPanel error={scopes.error} retry={() => scopes.refetch()} />
          {scope ? (
            <Workspace.Provider
              key={scope.id + ":" + accessEpoch}
              value={{ scope, refresh, setDirty }}
            >
              <Suspense fallback={<Spin description="正在打开功能" />}>
                <Routes>
                  <Route path="/work" element={<CreativePage />} />
                  <Route path="/materials" element={<MaterialsPage />} />
                  <Route path="/inbox" element={<InboxPage />} />
                  <Route
                    path="/admin/definitions"
                    element={<DefinitionsPage />}
                  />
                  <Route path="/admin/relations" element={<RelationsPage />} />
                  <Route path="/admin/maps" element={<MapPage />} />
                  <Route path="/admin/jobs" element={<JobsPage />} />
                  <Route path="/admin/exchange" element={<ExchangePage />} />
                  <Route path="/admin/quality" element={<QualityPage />} />
                  <Route
                    path="/admin/maintenance"
                    element={<MaintenancePage />}
                  />
                  <Route path="/admin/:page" element={<AdminPage />} />
                  <Route path="*" element={<CreativePage />} />
                </Routes>
              </Suspense>
            </Workspace.Provider>
          ) : (
            <div className="onboarding">
              <div className="brand-mark">N</div>
              <h1>从一个故事，或一份资料开始</h1>
              <p>创建作品、世界观或作者资料库。无需先准备完整大纲。</p>
              <Button
                size="large"
                type="primary"
                onClick={() => setNewScope(true)}
              >
                创建创作空间
              </Button>
            </div>
          )}
        </Layout.Content>
      </Layout>
      <Modal
        title="新建创作空间"
        open={newScope}
        onCancel={() => setNewScope(false)}
        onOk={() => form.submit()}
        destroyOnHidden
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={{ kind: "book" }}
          onFinish={async (values) => {
            try {
              const created = await api<Scope>("/scopes", "POST", values);
              cache.setQueriesData<Scope[]>({ queryKey: ["scopes"] }, (old) => [
                ...(old || []).filter((s) => s.id !== created.id),
                created,
              ]);
              setScopeId(created.id);
              setNewScope(false);
              form.resetFields();
              cache.invalidateQueries({ queryKey: ["scopes"] });
              message.success("创作空间已建立");
            } catch (e) {
              message.error((e as Error).message);
            }
          }}
        >
          <Form.Item name="name" label="名称" rules={[{ required: true }]}>
            <Input placeholder="作品、世界或资料库名称" />
          </Form.Item>
          <Form.Item name="kind" label="用途">
            <Select
              options={[
                ["book", "书项目"],
                ["author", "作者资料库"],
                ["universe", "共享宇宙"],
                ["series", "系列"],
                ["research", "拆书研究"],
                ["branch", "IF分支"],
              ].map(([value, label]) => ({ value, label }))}
            />
          </Form.Item>
          <Form.Item noStyle shouldUpdate={(a, b) => a.kind !== b.kind}>
            {({ getFieldValue }) =>
              getFieldValue("kind") === "branch" ? (
                <Form.Item
                  name="base_id"
                  label="固定基线来源"
                  rules={[{ required: true }]}
                >
                  <Select
                    options={scopes.data?.map((s) => ({
                      value: s.id,
                      label: `${s.name} · v${s.version}`,
                    }))}
                  />
                </Form.Item>
              ) : null
            }
          </Form.Item>
        </Form>
      </Modal>
    </Layout>
  );
}

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ConfigProvider
      locale={zhCN}
      theme={{
        token: {
          colorPrimary: "#245d4d",
          colorInfo: "#245d4d",
          colorBgLayout: "#f5f6f8",
          borderRadius: 8,
          fontFamily:
            '-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif',
        },
        components: {
          Layout: { headerBg: "#fff" },
          Menu: { itemSelectedBg: "#eaf2ee", itemSelectedColor: "#245d4d" },
        },
      }}
    >
      <AntApp>
        <QueryClientProvider client={client}>
          <BrowserRouter>
            <Shell />
          </BrowserRouter>
        </QueryClientProvider>
      </AntApp>
    </ConfigProvider>
  </React.StrictMode>,
);
