import { useQuery, useQueryClient } from "@tanstack/react-query";
import { App, Result, Tabs, Tag } from "antd";
import { useState } from "react";
import { api, type Json } from "../../shared/api";
import { ErrorPanel, PageTitle } from "../../shared/components/Feedback";
import { queryKeys } from "../../shared/queryKeys";
import { ApiConfigTab } from "./components/ApiConfigTab";
import { DefaultsTab } from "./components/DefaultsTab";
import "./model-settings.css";
import type { CapabilityId, Purpose, SettingsView } from "./modelsTypes";
import { SubscriptionPanel } from "./SubscriptionPanel";

export function ModelSettingsPage() {
  const { message } = App.useApp();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<
    "defaults" | "api" | "subscription"
  >("defaults");
  const [busyKey, setBusyKey] = useState("");

  const me = useQuery({
    queryKey: queryKeys.me(),
    queryFn: () => api<Json>("/me"),
  });
  const settings = useQuery({
    queryKey: queryKeys.modelSettings(),
    queryFn: () => api<SettingsView>("/model-settings"),
    enabled: !!me.data?.admin,
  });

  if (me.isPending) return null;
  if (!me.data?.admin) {
    return (
      <>
        <PageTitle
          title="AI 配置"
          note="模型登记与全局默认由系统管理员维护。密钥只留在服务端环境变量或本机 CLI 中，页面绝不接收或回传密钥。"
          actions={<Tag color="green">全局系统配置 · 所有作品共用</Tag>}
        />
        <Result
          status="403"
          title="当前账号不能修改模型登记"
          subTitle="请由系统管理员打开这一页。密钥不会发到浏览器。"
        />
      </>
    );
  }

  function remember(next: SettingsView) {
    queryClient.setQueryData(queryKeys.modelSettings(), next);
  }

  async function bindCapabilityDefault(payload: {
    capability: CapabilityId;
    source: "" | "api" | "subscription";
    configuration_id?: string;
    provider?: string;
    model_key?: string;
  }): Promise<boolean> {
    const key = `cap:${payload.capability}`;
    setBusyKey(key);
    try {
      const saved = await api<SettingsView>(
        "/model-settings/capability-defaults",
        "POST",
        {
          capability: payload.capability,
          source: payload.source,
          configuration_id: payload.configuration_id || "",
          provider: payload.provider || "",
          model_key: payload.model_key || "",
        },
      );
      remember(saved);
      const label =
        saved.capabilities?.find((c) => c.id === payload.capability)?.label ||
        payload.capability;
      message.success(
        payload.source
          ? `全局「${label}」默认已更新`
          : `全局「${label}」默认已清除`,
      );
      return true;
    } catch (error) {
      message.error((error as Error).message);
      return false;
    } finally {
      setBusyKey("");
    }
  }

  async function bindPurposeDefault(purpose: Purpose, configurationId: string) {
    const key = `purpose:${purpose}`;
    setBusyKey(key);
    try {
      const saved = await api<SettingsView>(
        "/model-settings/defaults",
        "POST",
        {
          purpose,
          configuration_id: configurationId,
        },
      );
      remember(saved);
      message.success("小说进阶工序默认已保存，只影响新任务");
    } catch (error) {
      message.error((error as Error).message);
    } finally {
      setBusyKey("");
    }
  }

  const busyCapability = busyKey.startsWith("cap:") ? busyKey.slice(4) : "";

  return (
    <div className="model-settings" data-component="model-settings">
      <PageTitle
        title="AI 配置"
        note="统一管理文本、生图、生视频、图生图、图生视频、文生视频六类全局默认模型，支持兼容 HTTP API 与本机 CLI OAuth 订阅双来源共用默认，并保留小说五段工序进阶覆写。"
        actions={<Tag color="green">全局系统配置 · 所有作品共用</Tag>}
      />
      <ErrorPanel error={settings.error} retry={() => settings.refetch()} />
      <Tabs
        activeKey={activeTab}
        onChange={(key) =>
          setActiveTab(key as "defaults" | "api" | "subscription")
        }
        items={[
          {
            key: "defaults",
            label: "默认配置",
            children: (
              <DefaultsTab
                data={settings.data}
                busyKey={busyKey}
                onBindCapability={bindCapabilityDefault}
                onBindPurpose={bindPurposeDefault}
                onJumpTab={(tab) => setActiveTab(tab)}
              />
            ),
          },
          {
            key: "api",
            label: "API 配置",
            children: (
              <ApiConfigTab
                data={settings.data}
                busyCapability={busyCapability}
                onUpdated={remember}
                onBindCapability={bindCapabilityDefault}
              />
            ),
          },
          {
            key: "subscription",
            label: "订阅配置",
            children: (
              <SubscriptionPanel
                settingsData={settings.data}
                busyCapability={busyCapability}
                onSettingsUpdated={remember}
                onBindCapability={bindCapabilityDefault}
              />
            ),
          },
        ]}
      />
    </div>
  );
}
