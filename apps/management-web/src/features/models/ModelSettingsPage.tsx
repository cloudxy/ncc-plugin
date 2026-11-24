import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Alert,
  App,
  Button,
  Card,
  Checkbox,
  Form,
  Input,
  Popconfirm,
  Result,
  Select,
  Switch,
  Tabs,
  Typography,
} from "antd";
import { useState } from "react";
import { api, type Json } from "../../shared/api";
import { ErrorPanel, PageTitle } from "../../shared/components/Feedback";
import "./model-settings.css";
import { SubscriptionPanel } from "./SubscriptionPanel";

type Purpose = "plan" | "write" | "revise" | "judge" | "judge_secondary";

type Configuration = {
  id: string;
  name: string;
  supplier: string;
  base_url: string;
  auth_ref: string;
  model_key: string;
  purposes: Purpose[];
  enabled: boolean;
  connection?: { status: string; credential: string; message: string };
};

type Draft = {
  name: string;
  supplier: string;
  base_url: string;
  auth_ref: string;
  model_key: string;
  purposes: Purpose[];
  enabled: boolean;
};

type SettingsView = {
  configurations: Configuration[];
  defaults: Record<string, string>;
  purposes: { id: Purpose; label: string }[];
  presets: Array<Draft & { id: string }>;
  source: string;
  effective: Record<
    string,
    {
      label: string;
      configuration_id: string;
      name: string;
      model_key: string;
      bound: boolean;
    }
  >;
  saved_id?: string;
};

const EMPTY: Draft = {
  name: "",
  supplier: "兼容接口",
  base_url: "",
  auth_ref: "NCC_MODEL_KEY",
  model_key: "",
  purposes: ["write"],
  enabled: false,
};

function draftOf(row: Configuration | null): Draft {
  if (!row) return EMPTY;
  return {
    name: row.name,
    supplier: row.supplier,
    base_url: row.base_url,
    auth_ref: row.auth_ref,
    model_key: row.model_key,
    purposes: row.purposes,
    enabled: row.enabled,
  };
}

export function ModelSettingsPage() {
  const { message } = App.useApp();
  const queryClient = useQueryClient();
  const [form] = Form.useForm<Draft>();
  const [selected, setSelected] = useState<string | null>(null);
  const [preset, setPreset] = useState<string | undefined>();
  const [checkNote, setCheckNote] = useState("");
  const [binds, setBinds] = useState<Record<string, string>>({});
  const me = useQuery({ queryKey: ["me"], queryFn: () => api<Json>("/me") });
  const settings = useQuery({
    queryKey: ["model-settings"],
    queryFn: () => api<SettingsView>("/model-settings"),
    enabled: !!me.data?.admin,
  });
  if (me.isPending) return null;
  if (!me.data?.admin)
    return (
      <>
        <PageTitle
          title="AI 配置"
          note="模型登记由系统管理员维护。密钥只留在服务端环境变量里，页面不接收密钥。"
        />
        <Result
          status="403"
          title="当前账号不能修改模型登记"
          subTitle="请由系统管理员打开这一页。密钥不会发到浏览器。"
        />
      </>
    );
  const data = settings.data;
  const configurations = data?.configurations || [];
  const purposes = data?.purposes || [];
  const selectedRow = configurations.find((row) => row.id === selected) || null;
  const purposeLabel = (id: string) =>
    purposes.find((item) => item.id === id)?.label || id;

  function remember(next: SettingsView) {
    queryClient.setQueryData(["model-settings"], next);
  }

  function showNew() {
    setSelected(null);
    setPreset(undefined);
    setCheckNote("");
    form.setFieldsValue(EMPTY);
  }

  function showRow(row: Configuration) {
    setSelected(row.id);
    setPreset(undefined);
    setCheckNote("");
    form.setFieldsValue(draftOf(row));
  }

  async function saveDraft(values: Draft) {
    if (!values.purposes?.length) {
      message.error("至少选择一个用途");
      return;
    }
    try {
      const saved = await api<SettingsView>(
        "/model-settings/configurations",
        "POST",
        selected ? { ...values, id: selected } : values,
      );
      remember(saved);
      const savedId = saved.saved_id || selected;
      const row =
        saved.configurations.find((item) => item.id === savedId) || null;
      setSelected(savedId);
      setPreset(undefined);
      setCheckNote("");
      form.setFieldsValue(draftOf(row));
      message.success("模型配置已保存");
    } catch (error) {
      message.error((error as Error).message);
    }
  }

  async function toggleEnabled(row: Configuration) {
    try {
      const saved = await api<SettingsView>(
        `/model-settings/configurations/${encodeURIComponent(row.id)}/enabled`,
        "POST",
        { enabled: !row.enabled },
      );
      remember(saved);
      const next = saved.configurations.find((item) => item.id === row.id);
      if (next) form.setFieldsValue(draftOf(next));
      message.success(row.enabled ? "已停用" : "已启用");
    } catch (error) {
      message.error((error as Error).message);
    }
  }

  async function remove(row: Configuration) {
    try {
      const saved = await api<SettingsView>(
        `/model-settings/configurations/${encodeURIComponent(row.id)}`,
        "DELETE",
      );
      remember(saved);
      if (selected === row.id) showNew();
      message.success("已删除");
    } catch (error) {
      message.error((error as Error).message);
    }
  }

  async function check(row: Configuration) {
    try {
      const value = await api<{ connection: { message: string } }>(
        `/model-settings/configurations/${encodeURIComponent(row.id)}/check`,
        "POST",
      );
      setCheckNote(value.connection.message);
      message.info(value.connection.message);
    } catch (error) {
      message.error((error as Error).message);
    }
  }

  async function saveDefault(purpose: Purpose) {
    const configurationId =
      binds[purpose] !== undefined
        ? binds[purpose]
        : data?.defaults?.[purpose] || "";
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
      setBinds((current) => ({
        ...current,
        [purpose]: saved.defaults?.[purpose] || "",
      }));
      message.success("默认用途已保存，只影响新任务");
    } catch (error) {
      message.error((error as Error).message);
    }
  }

  const note =
    data?.source === "environment"
      ? "还没有启用的模型登记。新任务继续使用进程环境变量。"
      : "新任务按默认用途取已启用的配置。没有指定时，用第一个包含该用途的已启用配置；仍然没有，才用进程环境。";

  return (
    <div className="model-settings" data-component="model-settings">
      <PageTitle
        title="AI 配置"
        note="订阅授权查看本机 Grok、Codex、AGY 登录态，不接收密钥。模型与连接可以登记多套接口，并把场景计划、正文与设定、修订、独立评价、第二评价分别绑定。检查和在线验证都不发起付费生成。已经开始的任务保留开始时的模型。"
      />
      <ErrorPanel error={settings.error} retry={() => settings.refetch()} />
      <Tabs
        items={[
          {
            key: "subscription",
            label: "订阅授权",
            children: <SubscriptionPanel />,
          },
          {
            key: "models",
            label: "模型与连接",
            children: (
              <>
                <Alert
                  type="info"
                  showIcon
                  title={note}
                  style={{ marginBottom: 16 }}
                />
                <div className="model-grid">
                  <aside className="model-list">
                    <Button onClick={showNew}>新建配置</Button>
                    {!configurations.length && (
                      <p className="model-empty">
                        还没有模型配置。新建一项后，可以按用途分别绑定。
                      </p>
                    )}
                    {configurations.map((row) => (
                      <button
                        type="button"
                        key={row.id}
                        className={
                          row.id === selected
                            ? "model-list-item selected"
                            : "model-list-item"
                        }
                        aria-current={row.id === selected ? "true" : undefined}
                        onClick={() => showRow(row)}
                      >
                        <strong>{row.name}</strong>
                        <small>
                          {row.supplier} · {row.model_key || "未填模型"} ·{" "}
                          {row.enabled ? "启用" : "停用"}
                        </small>
                        <small>
                          {row.purposes.map(purposeLabel).join("、")}
                        </small>
                      </button>
                    ))}
                  </aside>
                  <Card>
                    <Typography.Paragraph type="secondary">
                      {selectedRow ? "编辑配置" : "新建配置"}
                      。预设只填入表单，不会核对这些地址能否连通。
                    </Typography.Paragraph>
                    <Select
                      aria-label="供应商预设"
                      allowClear
                      placeholder="选择供应商预设，只填入表单"
                      style={{ width: "100%", marginBottom: 16 }}
                      value={preset}
                      options={(data?.presets || []).map((item) => ({
                        value: item.id,
                        label: item.name,
                      }))}
                      onChange={(id) => {
                        setPreset(id);
                        const item = data?.presets?.find(
                          (row) => row.id === id,
                        );
                        if (!item) return;
                        form.setFieldsValue({
                          name: item.name,
                          supplier: item.supplier,
                          base_url: item.base_url,
                          auth_ref: item.auth_ref,
                          model_key: item.model_key,
                          purposes: item.purposes,
                          enabled: false,
                        });
                      }}
                    />
                    <Form
                      form={form}
                      layout="vertical"
                      initialValues={EMPTY}
                      onFinish={saveDraft}
                    >
                      <Form.Item
                        name="name"
                        label="配置名称"
                        rules={[{ required: true, message: "填写配置名称" }]}
                      >
                        <Input
                          maxLength={80}
                          placeholder="例如 正文用 DeepSeek"
                        />
                      </Form.Item>
                      <Form.Item name="supplier" label="供应商或接口">
                        <Input maxLength={64} placeholder="兼容接口" />
                      </Form.Item>
                      <Form.Item
                        name="base_url"
                        label="网关地址"
                        extra="兼容 Chat JSON 的基础地址，请求发往 /chat/completions。不要把密钥写进地址。"
                      >
                        <Input
                          maxLength={512}
                          placeholder="https://example.test/v1"
                          autoComplete="off"
                        />
                      </Form.Item>
                      <Form.Item
                        name="auth_ref"
                        label="凭证环境变量名"
                        extra="只填变量名，例如 NCC_MODEL_KEY 或 DEEPSEEK_API_KEY。页面不接收密钥值。"
                      >
                        <Input
                          maxLength={128}
                          placeholder="NCC_MODEL_KEY"
                          autoComplete="off"
                        />
                      </Form.Item>
                      <Form.Item
                        name="model_key"
                        label="模型标识"
                        extra="供应商侧的模型名，不是密钥。"
                      >
                        <Input
                          maxLength={128}
                          placeholder="例如 deepseek-chat"
                          autoComplete="off"
                        />
                      </Form.Item>
                      <Form.Item
                        name="purposes"
                        label="适用用途"
                        rules={[
                          {
                            required: true,
                            type: "array",
                            min: 1,
                            message: "至少选择一个用途",
                          },
                        ]}
                      >
                        <Checkbox.Group
                          options={purposes.map((item) => ({
                            label: item.label,
                            value: item.id,
                          }))}
                        />
                      </Form.Item>
                      <Form.Item
                        name="enabled"
                        label="启用此配置"
                        valuePropName="checked"
                        extra="启用后才能被选为某个用途的默认。停用或删除会清掉指向它的默认用途。已经开始的任务不受影响。"
                      >
                        <Switch />
                      </Form.Item>
                      <Button type="primary" htmlType="submit">
                        保存配置
                      </Button>
                    </Form>
                    {selectedRow && (
                      <>
                        <Alert
                          style={{ marginTop: 16 }}
                          type={
                            selectedRow.connection?.status === "not_configured"
                              ? "warning"
                              : "info"
                          }
                          showIcon
                          title={
                            checkNote ||
                            selectedRow.connection?.message ||
                            "可以检查这项配置"
                          }
                        />
                        <div className="model-actions">
                          <Button onClick={() => check(selectedRow)}>
                            检查配置
                          </Button>
                          <Button onClick={() => toggleEnabled(selectedRow)}>
                            {selectedRow.enabled ? "停用此项" : "启用此项"}
                          </Button>
                          <Popconfirm
                            title="删除这个模型配置？"
                            description="已经开始的任务仍使用开始时记下的模型。指向它的默认用途会清空。"
                            okText="删除"
                            cancelText="取消"
                            onConfirm={() => remove(selectedRow)}
                          >
                            <Button danger>删除配置</Button>
                          </Popconfirm>
                        </div>
                      </>
                    )}
                  </Card>
                </div>
              </>
            ),
          },
          {
            key: "defaults",
            label: "默认用途",
            children: (
              <Card>
                <Typography.Paragraph type="secondary">
                  每个用途选择一项已启用、且声明了该用途的配置。选「不设置」后，新任务改用第一个符合的已启用配置；都没有时使用进程环境。第二评价两边都为空则不启用。已经开始的任务不改。
                </Typography.Paragraph>
                {purposes.map((item) => {
                  const options = configurations.filter(
                    (row) => row.enabled && row.purposes.includes(item.id),
                  );
                  const value =
                    binds[item.id] !== undefined
                      ? binds[item.id]
                      : data?.defaults?.[item.id] || "";
                  const effect = data?.effective?.[item.id];
                  const hint = !effect
                    ? ""
                    : effect.model_key
                      ? `${effect.bound ? "已绑定" : "未指定默认"}。新任务使用 ${effect.name}${effect.model_key ? ` · ${effect.model_key}` : ""}`
                      : item.id === "judge_secondary"
                        ? "未启用第二评价。"
                        : "这个用途还没有可用模型。新任务会停在未配置，不会生成演示内容。";
                  return (
                    <div className="model-default" key={item.id}>
                      <b>{item.label}</b>
                      <Select
                        aria-label={item.label}
                        value={value}
                        onChange={(next) =>
                          setBinds((current) => ({
                            ...current,
                            [item.id]: next,
                          }))
                        }
                        options={[
                          { value: "", label: "不设置" },
                          ...options.map((row) => ({
                            value: row.id,
                            label: `${row.name} · ${row.model_key}`,
                          })),
                        ]}
                      />
                      <Button
                        type="primary"
                        onClick={() => saveDefault(item.id)}
                      >
                        保存
                      </Button>
                      <p>{hint}</p>
                    </div>
                  );
                })}
              </Card>
            ),
          },
        ]}
      />
    </div>
  );
}
