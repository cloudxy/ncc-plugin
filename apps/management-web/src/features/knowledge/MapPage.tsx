import { useQuery } from "@tanstack/react-query";
import { Card, Typography } from "antd";
import { Suspense } from "react";
import { api, scoped, type Json } from "../../shared/api";
import { PageTitle } from "../../shared/components/Feedback";
import { useWorkspace } from "../../shared/WorkspaceContext";
import { MapCanvas } from "./components/KnowledgeVisuals";

export function MapPage() {
  const { scope } = useWorkspace();
  const entities = useQuery({
    queryKey: ["scope", scope.id, "map-entities"],
    queryFn: () =>
      api<Json>(scoped(scope.id, "/entities/search"), "POST", { limit: 200 }),
  });
  return (
    <>
      <PageTitle
        title="地图与地点"
        note="支持虚构坐标与本地底图。标注使用稳定地点身份，未知坐标保持未知。"
      />
      <Card>
        <Suspense fallback="加载地图">
          <MapCanvas scope={scope.id} entities={entities.data?.items || []} />
        </Suspense>
        <Typography.Paragraph type="secondary">
          当前显示已加载资料中的坐标。编辑地点的 coordinate
          属性维护位置，移动布局不会改变故事中的地理事实。
        </Typography.Paragraph>
      </Card>
    </>
  );
}
