import { useQuery } from "@tanstack/react-query";
import { Select } from "antd";
import { useState } from "react";
import { api, scoped, type Entity, type Json } from "../api";
import { useWorkspace } from "../WorkspaceContext";

export function ReferenceInput({
  value,
  onChange,
  multiple = false,
  includeRetired = false,
}: {
  value?: string | string[];
  onChange?: (value: any) => void;
  multiple?: boolean;
  includeRetired?: boolean;
}) {
  const { scope } = useWorkspace(),
    [q, setQ] = useState("");
  const query = useQuery({
    queryKey: ["scope", scope.id, "reference-search", q, includeRetired],
    queryFn: () =>
      api<Json>(scoped(scope.id, "/entities/search"), "POST", {
        q,
        limit: 50,
        include_deleted: includeRetired,
      }),
  });
  return (
    <Select
      style={{ width: "100%" }}
      aria-label="查找引用对象"
      value={value}
      onChange={onChange}
      mode={multiple ? "multiple" : undefined}
      allowClear
      showSearch
      filterOption={false}
      onSearch={setQ}
      placeholder="输入名称查找对象"
      options={query.data?.items.map((e: Entity) => ({
        value: e.id,
        label: `${e.name} · ${e.kind}`,
      }))}
    />
  );
}
