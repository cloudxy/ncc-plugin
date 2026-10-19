import { useQuery } from "@tanstack/react-query";
import { Alert } from "antd";
import cytoscape from "cytoscape";
import "ol/ol.css";
import { useEffect, useRef } from "react";
import { api, scoped, type Json } from "../../../shared/api";
import { ErrorPanel } from "../../../shared/components/Feedback";

export function GraphCanvas({
  scope,
  center,
}: {
  scope: string;
  center: string;
}) {
  const element = useRef<HTMLDivElement>(null);
  const query = useQuery({
    queryKey: ["scope", scope, "graph", center],
    queryFn: () => api<Json>(scoped(scope, `/graph/${center}`)),
  });
  useEffect(() => {
    if (!element.current || !query.data) return;
    const graph = cytoscape({
      container: element.current,
      elements: [
        ...query.data.nodes.map((n: Json) => ({
          data: { id: n.id, label: n.name },
        })),
        ...query.data.edges.map((e: Json) => ({
          data: {
            id: e.id,
            source: e.subject_id,
            target: e.object_id,
            label: e.predicate,
          },
        })),
      ],
      style: [
        {
          selector: "node",
          style: {
            "background-color": "#245d4d",
            label: "data(label)",
            color: "#293d35",
            "font-size": 12,
            "text-valign": "bottom",
            "text-margin-y": 9,
            width: 32,
            height: 32,
          },
        },
        {
          selector: "edge",
          style: {
            width: 1.5,
            "line-color": "#b6c9be",
            "target-arrow-color": "#9db4a7",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            label: "data(label)",
            "font-size": 10,
            color: "#72847a",
          },
        },
      ],
      layout: { name: "cose", animate: false, nodeRepulsion: () => 8000 },
      minZoom: 0.2,
      maxZoom: 3,
    });
    return () => graph.destroy();
  }, [query.data]);
  return (
    <>
      <ErrorPanel error={query.error} />
      {query.data?.truncated && (
        <Alert
          type="info"
          title="图谱已限定范围，请按节点继续查询；未加载不代表不存在"
        />
      )}
      <div
        ref={element}
        className="graph-canvas"
        aria-label="人物与组织关系图"
      />
      <details>
        <summary>查看可访问节点列表</summary>
        <ul>
          {query.data?.nodes.map((n: Json) => (
            <li key={n.id}>
              {n.name} · {n.kind}
            </li>
          ))}
        </ul>
      </details>
    </>
  );
}
