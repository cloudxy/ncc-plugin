import {
  BookOutlined,
  BranchesOutlined,
  ClockCircleOutlined,
  CloudServerOutlined,
  DatabaseOutlined,
  EditOutlined,
  EnvironmentOutlined,
  HistoryOutlined,
  ImportOutlined,
  InboxOutlined,
  LogoutOutlined,
  PlusOutlined,
  SafetyCertificateOutlined,
  SettingOutlined,
  StarOutlined,
} from "@ant-design/icons";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  App as AntApp,
  Button,
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
import { lazy, Suspense, useEffect, useRef, useState } from "react";
import { Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { api, scoped, setCSRF, type Json, type Scope } from "../shared/api";
import { ErrorPanel } from "../shared/components/Feedback";
import { Workspace } from "../shared/WorkspaceContext";
const CreativePage = lazy(() =>
  import("../features/creation/CreativePage").then((x) => ({
    default: x.CreativePage,
  })),
);
const InboxPage = lazy(() =>
  import("../features/inbox/InboxPage").then((x) => ({ default: x.InboxPage })),
);
const JobsPage = lazy(() =>
  import("../features/jobs/JobsPage").then((x) => ({ default: x.JobsPage })),
);
const MaterialsPage = lazy(() =>
  import("../features/knowledge/MaterialsPage").then((x) => ({
    default: x.MaterialsPage,
  })),
);
const DefinitionsPage = lazy(() =>
  import("../features/definitions/DefinitionsPage").then((x) => ({
    default: x.DefinitionsPage,
  })),
);
const RelationsPage = lazy(() =>
  import("../features/knowledge/RelationsPage").then((x) => ({
    default: x.RelationsPage,
  })),
);
const MapPage = lazy(() =>
  import("../features/knowledge/MapPage").then((x) => ({ default: x.MapPage })),
);
const ExchangePage = lazy(() =>
  import("../features/exchange/ExchangePage").then((x) => ({
    default: x.ExchangePage,
  })),
);
const QualityPage = lazy(() =>
  import("../features/quality/QualityPage").then((x) => ({
    default: x.QualityPage,
  })),
);
const AdminPage = lazy(() =>
  import("../features/administration/AdminPage").then((x) => ({
    default: x.AdminPage,
  })),
);
const MaintenancePage = lazy(() =>
  import("../features/knowledge/MaintenancePage").then((x) => ({
    default: x.MaintenancePage,
  })),
);

import { LoginPage } from "../features/session/LoginPage";
export function Shell() {
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
