import {
  AppstoreOutlined,
  BookOutlined,
  BranchesOutlined,
  ClockCircleOutlined,
  CloudServerOutlined,
  DatabaseOutlined,
  DownOutlined,
  EditOutlined,
  EnvironmentOutlined,
  FundOutlined,
  HistoryOutlined,
  ImportOutlined,
  InboxOutlined,
  KeyOutlined,
  LogoutOutlined,
  PartitionOutlined,
  PlusOutlined,
  RightOutlined,
  RobotOutlined,
  SafetyCertificateOutlined,
  SettingOutlined,
  StarOutlined,
} from "@ant-design/icons";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Alert,
  App as AntApp,
  Button,
  Form,
  Input,
  Layout,
  Modal,
  Select,
  Space,
  Spin,
  Tag,
  Typography,
} from "antd";
import {
  lazy,
  Suspense,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  type KeyboardEvent as ReactKeyboardEvent,
  type PointerEvent as ReactPointerEvent,
  type ReactNode,
} from "react";
import { Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { api, scoped, setCSRF, type Json, type Scope } from "../shared/api";
import { SCOPE_KINDS, kindLabel, scopeTag } from "../shared/scopeLabel";
import {
  bindStudioSessionOwner,
  clearAllStudioSessionDrafts,
  clearScopeStudioDrafts,
  pruneStudioDraftScopes,
  syncScopeStudioActions,
} from "../shared/studioApi";
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
const ModelSettingsPage = lazy(() =>
  import("../features/models/ModelSettingsPage").then((x) => ({
    default: x.ModelSettingsPage,
  })),
);
const BlueprintPage = lazy(() =>
  import("../features/blueprint/BlueprintPage").then((x) => ({
    default: x.BlueprintPage,
  })),
);
const CommonsPage = lazy(() =>
  import("../features/commons/CommonsPage").then((x) => ({
    default: x.CommonsPage,
  })),
);
const MarketPage = lazy(() =>
  import("../features/market/MarketPage").then((x) => ({
    default: x.MarketPage,
  })),
);

import { CredentialChangeModal } from "../features/session/CredentialChangeModal";
import { LoginPage } from "../features/session/LoginPage";

const DAILY: [string, string, ReactNode][] = [
  ["/work", "创作台", <EditOutlined />],
  ["/blueprint", "大纲与暗线", <PartitionOutlined />],
  ["/materials", "作品资料", <BookOutlined />],
  ["/commons", "公共陈列库", <AppstoreOutlined />],
  ["/market", "市场与风向", <FundOutlined />],
  ["/inbox", "我的待办", <InboxOutlined />],
];
const ADVANCED: [string, string, ReactNode][] = [
  ["/admin/maintenance", "身份与历史维护", <HistoryOutlined />],
  ["/admin/definitions", "定义中心", <DatabaseOutlined />],
  ["/admin/relations", "关系与时间", <BranchesOutlined />],
  ["/admin/maps", "地图与地点", <EnvironmentOutlined />],
  ["/admin/quality", "质量与评分", <StarOutlined />],
  ["/admin/exchange", "导入与导出", <ImportOutlined />],
  ["/admin/jobs", "任务中心", <ClockCircleOutlined />],
  ["/admin/audit", "操作审计", <SafetyCertificateOutlined />],
  ["/admin/settings", "成员与设置", <SettingOutlined />],
  ["/admin/models", "AI 配置", <RobotOutlined />],
  ["/admin/operations", "运行管理", <CloudServerOutlined />],
];
const NAV_KEYS = new Set([...DAILY, ...ADVANCED].map(([key]) => key));

type ScrollShot = { side: number; main: number };
type LeavePending = ScrollShot & { type: "nav" | "scope"; key: string };
type ScrollPlan = ScrollShot & { focusKey?: string };

export function Shell() {
  const cache = useQueryClient(),
    nav = useNavigate(),
    location = useLocation(),
    { message } = AntApp.useApp();
  const [authenticated, setAuthenticated] = useState(true),
    [scopeId, setScopeId] = useState(""),
    [dirty, setDirty] = useState(false),
    [newScope, setNewScope] = useState(false),
    [renameOpen, setRenameOpen] = useState(false),
    [credentialModalOpen, setCredentialModalOpen] = useState(false),
    [renaming, setRenaming] = useState(false),
    [creating, setCreating] = useState(false),
    [accessEpoch, setAccessEpoch] = useState(0),
    [loginEpoch, setLoginEpoch] = useState(0),
    [pending, setPending] = useState<LeavePending | null>(null),
    [advancedOpen, setAdvancedOpen] = useState(() =>
      window.location.pathname.startsWith("/admin/"),
    );
  const [form] = Form.useForm();
  const [renameForm] = Form.useForm();
  const sidebarRef = useRef<HTMLElement>(null),
    mainRef = useRef<HTMLDivElement>(null),
    stayRef = useRef<HTMLButtonElement>(null),
    liveScroll = useRef<ScrollShot>({ side: 0, main: 0 }),
    gestureScroll = useRef<ScrollShot | null>(null),
    scrollPlan = useRef<ScrollPlan | null>(null);
  const me = useQuery({
    queryKey: ["me"],
    queryFn: () => api<Json>("/me"),
    enabled: authenticated,
    retry: false,
  });
  const mustChangeCredentials = Boolean(me.data?.must_change_credentials);
  const credentialChangeEnforced =
    mustChangeCredentials && Boolean(me.data?.credential_change_enforced);
  const credentialChangeReminder =
    typeof me.data?.credential_change_reminder === "string" &&
    me.data.credential_change_reminder.trim()
      ? me.data.credential_change_reminder
      : credentialChangeEnforced
        ? "当前通过真实地址访问且正在使用默认管理员账号，请先修改账号和密码后再继续使用。"
        : "首次使用默认管理员账号（admin），请及时修改账号名和密码。";
  const scopes = useQuery({
    queryKey: ["scopes", me.data?.id],
    queryFn: () => api<Scope[]>("/scopes"),
    enabled: !!me.data && authenticated && !credentialChangeEnforced,
  });
  const scope = scopeId
    ? scopes.data?.find((x) => x.id === scopeId)
    : scopes.data?.[0];
  const sessionKey =
    authenticated && !me.error && me.data?.id
      ? `${me.data.id}:${me.data.csrf || "cookie"}:${loginEpoch}`
      : "";
  bindStudioSessionOwner(sessionKey || null);
  const shellReady =
    authenticated &&
    !me.error &&
    !me.isPending &&
    !credentialChangeEnforced &&
    !scopes.isPending;
  const accessStamp = useRef(""),
    activeScope = useRef("");
  activeScope.current = scope?.id || "";
  function resetAccess(sid: string) {
    clearScopeStudioDrafts(sid);
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
  useLayoutEffect(() => {
    const root = document.documentElement;
    if (!shellReady) {
      root.classList.remove("shell-lock");
      return;
    }
    root.classList.add("shell-lock");
    return () => root.classList.remove("shell-lock");
  }, [shellReady]);
  useLayoutEffect(() => {
    const plan = scrollPlan.current;
    if (!plan) return;
    scrollPlan.current = null;
    applyScroll(plan);
    requestAnimationFrame(() => applyScroll(plan));
  }, [location.pathname, scope?.id, pending]);
  function readScroll(): ScrollShot {
    return {
      side: sidebarRef.current?.scrollTop ?? 0,
      main: mainRef.current?.scrollTop ?? 0,
    };
  }
  function trackScroll() {
    if (gestureScroll.current) return;
    liveScroll.current = readScroll();
  }
  function beginGesture(event: ReactPointerEvent | ReactKeyboardEvent) {
    const target = event.target;
    if (!(target instanceof Element) || !target.closest(".nav-item")) return;
    const shot = readScroll();
    liveScroll.current = shot;
    gestureScroll.current = shot;
  }
  function endGesture() {
    gestureScroll.current = null;
  }
  function shotScroll() {
    const shot = gestureScroll.current ?? liveScroll.current;
    gestureScroll.current = null;
    return shot;
  }
  function applyScroll(plan: ScrollPlan) {
    const sideEl = sidebarRef.current,
      mainEl = mainRef.current;
    if (mainEl) mainEl.scrollTop = plan.main;
    if (sideEl) sideEl.scrollTop = plan.side;
    if (plan.focusKey) {
      sideEl
        ?.querySelector<HTMLElement>(
          `[data-nav-key="${CSS.escape(plan.focusKey)}"]`,
        )
        ?.focus({ preventScroll: true });
    }
    if (mainEl) mainEl.scrollTop = plan.main;
    if (sideEl) sideEl.scrollTop = plan.side;
  }
  function paintScroll(plan: ScrollPlan) {
    applyScroll(plan);
    requestAnimationFrame(() => applyScroll(plan));
  }
  useEffect(() => {
    if (scopes.data) {
      pruneStudioDraftScopes(scopes.data.map((item) => item.id));
    }
  }, [scopes.data]);
  useEffect(() => {
    if (scope) {
      syncScopeStudioActions(scope.id, scope.actions);
    }
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
    if (location.pathname.startsWith("/admin/")) setAdvancedOpen(true);
  }, [location.pathname]);
  useEffect(() => {
    const expire = () => {
      clearAllStudioSessionDrafts();
      setDirty(false);
      setCredentialModalOpen(false);
      setLoginEpoch((x) => x + 1);
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
    if (!scope || credentialChangeEnforced) return;
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
  }, [scope?.id, credentialChangeEnforced]);
  async function handleLogout() {
    try {
      await api("/auth/logout", "POST");
    } finally {
      clearAllStudioSessionDrafts();
      setCSRF("");
      setDirty(false);
      setCredentialModalOpen(false);
      setLoginEpoch((x) => x + 1);
      setAuthenticated(false);
      cache.clear();
    }
  }
  function handleCredentialChanged(updatedMe: Json) {
    if (typeof updatedMe?.csrf === "string") {
      setCSRF(updatedMe.csrf);
    }
    setCredentialModalOpen(false);
    cache.setQueryData(["me"], updatedMe);
    cache.invalidateQueries({ queryKey: ["me"] });
    cache.invalidateQueries({ queryKey: ["scopes"] });
    message.success("账号与密码已更新");
  }
  function navigate(key: string) {
    const shot = shotScroll();
    if (dirty) {
      applyScroll({ ...shot });
      setPending({ type: "nav", key, ...shot });
      return;
    }
    const plan = { ...shot, main: 0, focusKey: key };
    if (location.pathname !== key) {
      scrollPlan.current = plan;
      nav(key);
    }
    paintScroll(plan);
  }
  function keepEditing() {
    if (!pending) return;
    const plan = {
      side: pending.side,
      main: pending.main,
      focusKey: pending.type === "nav" ? pending.key : undefined,
    };
    scrollPlan.current = plan;
    setPending(null);
    paintScroll(plan);
  }
  function confirmLeave() {
    if (!pending) return;
    const plan = {
      side: pending.side,
      main: 0,
      focusKey: pending.type === "nav" ? pending.key : undefined,
    };
    scrollPlan.current = plan;
    setDirty(false);
    if (pending.type === "nav") nav(pending.key);
    else setScopeId(pending.key);
    setPending(null);
    paintScroll(plan);
  }
  if (!authenticated || me.error)
    return (
      <LoginPage
        done={() => {
          clearAllStudioSessionDrafts();
          setDirty(false);
          setCredentialModalOpen(false);
          setLoginEpoch((x) => x + 1);
          setAuthenticated(true);
          cache.clear();
          me.refetch();
        }}
      />
    );
  if (me.isPending)
    return (
      <div className="fullscreen">
        <Spin description="正在打开私有工作台" />
      </div>
    );
  if (credentialChangeEnforced)
    return (
      <div className="fullscreen">
        <div className="brand-mark">N</div>
        <Typography.Title level={3} style={{ margin: 0 }}>
          首次登录安全要求
        </Typography.Title>
        <Typography.Text type="secondary">
          {credentialChangeReminder}
        </Typography.Text>
        <CredentialChangeModal
          open
          enforced
          currentUsername={
            typeof me.data?.username === "string" ? me.data.username : "admin"
          }
          mustChangeDefault
          onSuccess={handleCredentialChanged}
          onLogout={handleLogout}
        />
      </div>
    );
  if (scopes.isPending)
    return (
      <div className="fullscreen">
        <Spin description="正在打开私有工作台" />
      </div>
    );
  const current = NAV_KEYS.has(location.pathname) ? location.pathname : "/work";
  function item(key: string, label: string, icon: ReactNode) {
    return (
      <button
        key={key}
        type="button"
        className="nav-item"
        data-nav-key={key}
        aria-label={label}
        aria-current={current === key ? "page" : undefined}
        onClick={() => navigate(key)}
      >
        <span aria-hidden="true">{icon}</span>
        <span>{label}</span>
      </button>
    );
  }
  const scopeFailed = scopes.isError;
  return (
    <Layout className="app-layout" data-component="split-scroll">
      <aside
        className="sidebar"
        ref={sidebarRef}
        onScroll={trackScroll}
        onPointerDown={beginGesture}
        onPointerUp={endGesture}
        onKeyDown={(event) => {
          if (event.key === "Enter" || event.key === " ") beginGesture(event);
        }}
        onKeyUp={(event) => {
          if (event.key === "Enter" || event.key === " ") endGesture();
        }}
      >
        <div className="brand">
          <div className="brand-mark small">N</div>
          <div>
            <b>NCC</b>
            <small>创作工作台</small>
          </div>
        </div>
        <nav aria-label="创作后台导航">
          {DAILY.map(([key, label, icon]) => item(key, label, icon))}
          <button
            type="button"
            className="nav-item"
            aria-label="高级管理"
            aria-expanded={advancedOpen}
            aria-controls="advanced-nav"
            onClick={() => setAdvancedOpen((open) => !open)}
          >
            <span aria-hidden="true">
              {advancedOpen ? <DownOutlined /> : <RightOutlined />}
            </span>
            <span>高级管理</span>
          </button>
          {advancedOpen ? (
            <div id="advanced-nav">
              {ADVANCED.map(([key, label, icon]) => item(key, label, icon))}
            </div>
          ) : null}
        </nav>
        <div className="sidebar-footer">
          <span className="live-dot" />
          私有资料空间 <Tag bordered={false}>v4.0</Tag>
          <small>创作、事实与修改都有来处。</small>
        </div>
      </aside>
      <div className="workspace" ref={mainRef} onScroll={trackScroll}>
        <header className="topbar">
          <Space>
            <Select
              aria-label="当前作品或资料库"
              value={scopeFailed ? undefined : scope?.id}
              disabled={scopeFailed}
              style={{ width: 240 }}
              options={
                scopeFailed
                  ? []
                  : scopes.data?.map((s) => ({
                      value: s.id,
                      label: s.name,
                    }))
              }
              onChange={(value) => {
                const shot = readScroll();
                liveScroll.current = shot;
                if (dirty) {
                  applyScroll(shot);
                  setPending({ type: "scope", key: value, ...shot });
                  return;
                }
                setScopeId(value);
              }}
            />
            <Button
              icon={<EditOutlined />}
              aria-label="修改当前范围名称"
              title={
                scope?.owner === false
                  ? "只有范围所有者可修改名称"
                  : "修改当前范围名称"
              }
              disabled={!scope || scope.owner === false}
              onClick={() => {
                renameForm.setFieldsValue({ name: scope?.name });
                setRenameOpen(true);
              }}
            />
            {scope || scopeFailed ? (
              <Button
                icon={<PlusOutlined />}
                onClick={() => setNewScope(true)}
                aria-label="新建作品或资料库"
              />
            ) : null}
            {scope && !scopeFailed && (
              <Tag>{scopeTag(scope.kind, scope.version)}</Tag>
            )}
          </Space>
          <Space>
            <Typography.Text type="secondary">
              {me.data?.username}
            </Typography.Text>
            <Button
              type="text"
              size="small"
              icon={<KeyOutlined />}
              aria-label="修改账号密码"
              onClick={() => setCredentialModalOpen(true)}
            >
              <span className="topbar-logout-label">修改账号密码</span>
            </Button>
            <Button
              className="topbar-ai"
              icon={<RobotOutlined />}
              aria-label="AI 配置"
              onClick={() => navigate("/admin/models")}
            >
              <span className="topbar-ai-label">AI 配置</span>
            </Button>
            <Button
              type="text"
              icon={<LogoutOutlined />}
              aria-label="退出"
              onClick={handleLogout}
            >
              <span className="topbar-logout-label">退出</span>
            </Button>
          </Space>
        </header>
        {mustChangeCredentials && !credentialChangeEnforced ? (
          <Alert
            type="warning"
            banner
            showIcon
            style={{ marginBottom: 0 }}
            title={`${credentialChangeReminder}（第一次使用时必须修改默认账号与密码）`}
            action={
              <Button
                size="small"
                type="primary"
                onClick={() => setCredentialModalOpen(true)}
              >
                立即修改账号密码
              </Button>
            }
          />
        ) : null}
        <div className="content">
          {scopeFailed ? (
            <div className="scope-failure" role="alert">
              <p>没有取到范围列表。</p>
              {scopes.error instanceof Error && scopes.error.message ? (
                <p>{scopes.error.message}</p>
              ) : null}
              <Button onClick={() => scopes.refetch()}>重试</Button>
            </div>
          ) : scope ? (
            <Workspace.Provider
              key={scope.id + ":" + accessEpoch}
              value={{ scope, sessionKey, refresh, setDirty }}
            >
              <Suspense fallback={<Spin description="正在打开功能" />}>
                <Routes>
                  <Route path="/work" element={<CreativePage />} />
                  <Route path="/blueprint" element={<BlueprintPage />} />
                  <Route path="/materials" element={<MaterialsPage />} />
                  <Route path="/commons" element={<CommonsPage />} />
                  <Route path="/market" element={<MarketPage />} />
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
                  <Route path="/admin/models" element={<ModelSettingsPage />} />
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
                aria-label="新建作品或资料库"
                onClick={() => setNewScope(true)}
              >
                创建创作空间
              </Button>
            </div>
          )}
        </div>
      </div>
      <Modal
        title="保留当前未保存内容？"
        open={pending !== null}
        onCancel={keepEditing}
        closable={false}
        mask={{ closable: false }}
        footer={
          <div className="leave-actions">
            <Button type="primary" ref={stayRef} onClick={keepEditing}>
              继续编辑
            </Button>
            <Button onClick={confirmLeave}>离开</Button>
          </div>
        }
        afterOpenChange={(open) => {
          if (open) stayRef.current?.focus();
        }}
        destroyOnHidden
      >
        <p>
          尚未自动保存成功的本次输入，离开后不再保留。已经自动保存成功的草稿，回到创作台时会恢复。
        </p>
      </Modal>
      <Modal
        title="修改名称"
        open={renameOpen}
        onCancel={() => setRenameOpen(false)}
        onOk={() => renameForm.submit()}
        okText={renaming ? "正在保存" : "保存"}
        confirmLoading={renaming}
        destroyOnHidden
      >
        <Form
          form={renameForm}
          layout="vertical"
          onFinish={async (values) => {
            if (!scope) return;
            setRenaming(true);
            try {
              const updated = await api<Scope>(
                `/scopes/${scope.id}`,
                "PATCH",
                values,
              );
              cache.setQueriesData<Scope[]>({ queryKey: ["scopes"] }, (old) =>
                (old || []).map((item) =>
                  item.id === updated.id ? { ...item, ...updated } : item,
                ),
              );
              setRenameOpen(false);
              message.success("名称已更新");
            } catch (e) {
              message.error((e as Error).message);
            } finally {
              setRenaming(false);
            }
          }}
        >
          <Form.Item
            name="name"
            label="名称"
            rules={[{ required: true, whitespace: true, max: 256 }]}
          >
            <Input placeholder="作品、世界或资料库名称" maxLength={256} />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        title="新建创作空间"
        open={newScope}
        onCancel={() => setNewScope(false)}
        onOk={() => form.submit()}
        confirmLoading={creating}
        destroyOnHidden
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={{ kind: "book" }}
          onFinish={async (values) => {
            if (values.kind === "branch" && !values.base_id) return;
            setCreating(true);
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
            } finally {
              setCreating(false);
            }
          }}
        >
          <Form.Item name="name" label="名称" rules={[{ required: true }]}>
            <Input placeholder="作品、世界或资料库名称" />
          </Form.Item>
          <Form.Item name="kind" label="用途">
            <Select
              options={SCOPE_KINDS.map((value) => ({
                value,
                label: kindLabel(value),
              }))}
            />
          </Form.Item>
          <Form.Item noStyle shouldUpdate={(a, b) => a.kind !== b.kind}>
            {({ getFieldValue }) =>
              getFieldValue("kind") === "branch" ? (
                <Form.Item
                  name="base_id"
                  label="固定基线来源"
                  rules={[
                    {
                      required: true,
                      message: "IF分支必须选择基线，否则不能提交。",
                    },
                  ]}
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
      <CredentialChangeModal
        open={credentialModalOpen}
        enforced={false}
        currentUsername={
          typeof me.data?.username === "string" ? me.data.username : ""
        }
        mustChangeDefault={mustChangeCredentials}
        onClose={() => setCredentialModalOpen(false)}
        onSuccess={handleCredentialChanged}
        onLogout={handleLogout}
      />
    </Layout>
  );
}
