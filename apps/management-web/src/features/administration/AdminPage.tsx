import { PlusOutlined } from "@ant-design/icons";
import { useQuery } from "@tanstack/react-query";
import { Button, Card, Form, Tag, Typography } from "antd";
import { useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { api, scoped, type Json, type Scope } from "../../shared/api";
import { PageTitle, Permission } from "../../shared/components/Feedback";
import { queryKeys } from "../../shared/queryKeys";
import { useWorkspace } from "../../shared/WorkspaceContext";
import { AuditLogPanel } from "./components/AuditLogPanel";
import { OperationsPanel } from "./components/OperationsPanel";
import { ScopeManagementCard } from "./components/ScopeManagementCard";
import { ScopeMembersCard } from "./components/ScopeMembersCard";
import { ScopedTokensCard } from "./components/ScopedTokensCard";
import { SystemUsersCard } from "./components/SystemUsersCard";
import { TrustControls } from "./components/TrustControls";
import "./settings.css";

export function AdminPage() {
  const { page } = useParams();
  const { scope } = useWorkspace();
  const [userOpen, setUserOpen] = useState(false);
  const [dirQuery, setDirQuery] = useState("");
  const [auditAction, setAuditAction] = useState<string>();
  const [auditActor, setAuditActor] = useState<string>();
  const [memberForm] = Form.useForm();

  const me = useQuery({
    queryKey: queryKeys.me(),
    queryFn: () => api<Json>("/me"),
  });
  const isSystemAdmin = Boolean(me.data?.admin);
  const canScopeAdmin = scope.actions.includes("admin");

  const audit = useQuery({
    queryKey: queryKeys.audit(scope.id, {
      action: auditAction,
      actor_id: auditActor,
    }),
    queryFn: () => {
      const qs = new URLSearchParams();
      if (auditAction) qs.set("action", auditAction);
      if (auditActor) qs.set("actor_id", auditActor);
      qs.set("limit", "100");
      const suffix = qs.toString();
      return api<Json[]>(
        scoped(scope.id, `/audit${suffix ? `?${suffix}` : ""}`),
      );
    },
    enabled: page === "audit" && canScopeAdmin,
  });

  const members = useQuery({
    queryKey: queryKeys.members(scope.id),
    queryFn: () => api<Json[]>(scoped(scope.id, "/members")),
    enabled: (page === "settings" || page === "audit") && canScopeAdmin,
  });

  const users = useQuery({
    queryKey: queryKeys.users(),
    queryFn: () => api<Json[]>("/users"),
    enabled: page === "settings" && isSystemAdmin,
  });

  const directory = useQuery({
    queryKey: queryKeys.userDirectory(dirQuery),
    queryFn: () => {
      const qs = dirQuery.trim()
        ? `?q=${encodeURIComponent(dirQuery.trim())}`
        : "";
      return api<{ id: string; username: string }[]>(`/users/directory${qs}`);
    },
    enabled: (page === "settings" || page === "audit") && canScopeAdmin,
  });

  const tokens = useQuery({
    queryKey: queryKeys.tokens(scope.id),
    queryFn: () => api<Json[]>(scoped(scope.id, "/tokens")),
    enabled: page === "settings" && canScopeAdmin,
  });

  const allScopes = useQuery({
    queryKey: queryKeys.allScopes(me.data?.id),
    queryFn: () => api<Scope[]>("/scopes?include_archived=true"),
    enabled: page === "settings" && !!me.data?.id,
  });

  const operations = useQuery({
    queryKey: queryKeys.operations(scope.id),
    queryFn: () => api<Json>(scoped(scope.id, "/operations")),
    enabled: page === "operations" && scope.actions.includes("operate"),
    refetchInterval: 10000,
  });

  const userSelectOptions = useMemo(() => {
    const map = new Map<string, string>();
    for (const item of directory.data || []) {
      map.set(item.username, item.username);
    }
    for (const item of users.data || []) {
      if (item.active !== false && item.username) {
        map.set(String(item.username), String(item.username));
      }
    }
    return [...map.values()].map((username) => ({
      value: username,
      label: username,
    }));
  }, [directory.data, users.data]);

  const auditActorOptions = useMemo(() => {
    const map = new Map<string, string>();
    for (const item of directory.data || []) {
      map.set(item.id, item.username);
    }
    for (const item of members.data || []) {
      const uid = String(item.user_id || item.id || "");
      if (uid && item.username) map.set(uid, String(item.username));
    }
    for (const row of audit.data || []) {
      if (row.actor_id) {
        map.set(
          String(row.actor_id),
          String(row.actor_username || String(row.actor_id).slice(0, 8)),
        );
      }
    }
    return [...map.entries()].map(([value, label]) => ({ value, label }));
  }, [directory.data, members.data, audit.data]);

  if (page === "audit") {
    return (
      <AuditLogPanel
        allowed={canScopeAdmin}
        auditData={audit.data}
        auditLoading={audit.isPending}
        auditError={audit.error}
        onRetry={() => void audit.refetch()}
        auditAction={auditAction}
        onAuditActionChange={setAuditAction}
        auditActor={auditActor}
        auditActorOptions={auditActorOptions}
        onAuditActorChange={setAuditActor}
        onClearFilters={() => {
          setAuditAction(undefined);
          setAuditActor(undefined);
        }}
      />
    );
  }

  if (page === "operations") {
    return (
      <OperationsPanel
        allowed={scope.actions.includes("operate")}
        data={operations.data}
        isPending={operations.isPending}
        error={operations.error}
        onRetry={() => void operations.refetch()}
      />
    );
  }

  const archivedScopes = (allScopes.data || []).filter((s) => s.archived);

  return (
    <Permission allowed={canScopeAdmin}>
      <div className="settings-page" data-component="settings-columns">
        <PageTitle
          title="成员与设置"
          note="真实用户权限与小说人物认知分别管理，范围凭据不能扩大账号现有权限。"
          actions={
            isSystemAdmin && (
              <Button icon={<PlusOutlined />} onClick={() => setUserOpen(true)}>
                建立账号
              </Button>
            )
          }
        />
        <div className="settings-columns">
          <div className="settings-pane">
            <SystemUsersCard
              isSystemAdmin={isSystemAdmin}
              currentUserId={
                typeof me.data?.id === "string" ? me.data.id : undefined
              }
              usersData={users.data}
              usersLoading={users.isPending}
              usersError={users.error}
              onRefetchUsers={() => users.refetch()}
              onRefetchDirectory={() => directory.refetch()}
              userOpen={userOpen}
              onOpenCreateUser={() => setUserOpen(true)}
              onCloseCreateUser={() => setUserOpen(false)}
              onSelectAsMember={(username, actions) =>
                memberForm.setFieldsValue({ username, actions })
              }
              onUserCreated={(username) =>
                memberForm.setFieldsValue({ username })
              }
            />

            <ScopeMembersCard
              scope={scope}
              memberForm={memberForm}
              membersData={members.data}
              membersLoading={members.isPending}
              membersError={members.error}
              onRefetchMembers={() => members.refetch()}
              userSelectOptions={userSelectOptions}
              onDirQueryChange={setDirQuery}
            />

            <ScopeManagementCard
              scope={scope}
              archivedScopes={archivedScopes}
              onRefetchAllScopes={() => allScopes.refetch()}
            />
          </div>

          <div className="settings-pane">
            <ScopedTokensCard
              scope={scope}
              tokensData={tokens.data}
              tokensLoading={tokens.isPending}
            />

            <Card title="自动定稿策略">
              <Typography.Paragraph>
                普通创作默认集中审核。托管需明确对象、时间与次数，并完成对应评分策略的留出校准；授权可随时撤销。
              </Typography.Paragraph>
              <Tag>质量线 85 · 最多修订 2 次</Tag>
            </Card>

            <div>
              <TrustControls />
            </div>
          </div>
        </div>
      </div>
    </Permission>
  );
}
