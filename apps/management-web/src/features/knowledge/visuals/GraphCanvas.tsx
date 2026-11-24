import { useQuery } from "@tanstack/react-query";
import { Alert } from "antd";
import cytoscape from "cytoscape";
import { useEffect, useMemo, useRef } from "react";
import { api, scoped, type Json } from "../../../shared/api";
import { ErrorPanel } from "../../../shared/components/Feedback";

export type GraphNode = { id: string; name: string };
export type GraphEdge = {
  id: string;
  subject_id: string;
  object_id: string;
  predicate: string;
};

function GraphBoard({
  nodes,
  edges,
  labelled,
}: {
  nodes: GraphNode[];
  edges: GraphEdge[];
  labelled: boolean;
}) {
  const element = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const host = element.current;
    if (!host) return;
    const tone = getComputedStyle(host).color || "CanvasText";
    const links = edges.filter(
      (edge) => edge.id && edge.subject_id && edge.object_id,
    );
    const graph = cytoscape({
      container: host,
      elements: [
        ...nodes.map((node) => ({
          data: { id: node.id, label: node.name },
        })),
        ...links.map((edge) => ({
          data: {
            id: edge.id,
            source: edge.subject_id,
            target: edge.object_id,
            label: edge.predicate,
          },
        })),
      ],
      style: [
        {
          selector: "node",
          style: {
            "background-color": tone,
            label: "data(label)",
            color: tone,
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
            "line-color": tone,
            "target-arrow-color": tone,
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            label: "data(label)",
            "font-size": 10,
            color: tone,
          },
        },
      ],
      layout: { name: "cose", animate: false },
      minZoom: 0.2,
      maxZoom: 3,
    });
    return () => graph.destroy();
  }, [nodes, edges]);
  return (
    <div
      ref={element}
      className="graph-canvas"
      data-component={labelled ? "relation-board" : undefined}
      aria-label="人物与组织关系图"
    />
  );
}

function QueriedGraph({ scope, center }: { scope: string; center: string }) {
  const query = useQuery({
    queryKey: ["scope", scope, "graph", center],
    queryFn: () => api<Json>(scoped(scope, `/graph/${center}`)),
    retry: false,
  });
  const data = query.isSuccess ? query.data : undefined;
  const nodes = useMemo<GraphNode[]>(() => {
    const rows = Array.isArray(data?.nodes) ? data.nodes : [];
    return rows.map((node: Json) => ({
      id: String(node.id),
      name: typeof node.name === "string" ? node.name : "",
    }));
  }, [data]);
  const edges = useMemo<GraphEdge[]>(() => {
    const rows = Array.isArray(data?.edges) ? data.edges : [];
    return rows
      .filter((edge: Json) => edge.id && edge.subject_id && edge.object_id)
      .map((edge: Json) => ({
        id: String(edge.id),
        subject_id: String(edge.subject_id),
        object_id: String(edge.object_id),
        predicate: typeof edge.predicate === "string" ? edge.predicate : "",
      }));
  }, [data]);
  return (
    <>
      <ErrorPanel error={query.isError ? query.error : undefined} />
      {data?.truncated === true && (
        <Alert
          type="info"
          title="图谱已限定范围，请按节点继续查询；未加载不代表不存在"
        />
      )}
      {query.isSuccess && (
        <GraphBoard nodes={nodes} edges={edges} labelled={false} />
      )}
      <details>
        <summary>查看可访问节点列表</summary>
        <ul>
          {nodes.map((node) => (
            <li key={node.id}>{node.name}</li>
          ))}
        </ul>
      </details>
    </>
  );
}

export function GraphCanvas(
  props:
    | { nodes: GraphNode[]; edges: GraphEdge[] }
    | { scope: string; center: string },
) {
  if ("nodes" in props)
    return <GraphBoard nodes={props.nodes} edges={props.edges} labelled />;
  return <QueriedGraph scope={props.scope} center={props.center} />;
}
