import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Alert, Button, Input, Select, Skeleton, Space } from "antd";
import { Suspense, useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  api,
  scoped,
  type Definition,
  type Entity,
  type Json,
} from "../../shared/api";
import { NoData, PageTitle } from "../../shared/components/Feedback";
import { scopeLine } from "../../shared/scopeLabel";
import { useWorkspace } from "../../shared/WorkspaceContext";
import { effectDetail } from "../creation/effectDetail";
import { readCoordinate } from "./coordinates";
import { MapCanvas } from "./components/KnowledgeVisuals";
import "./visuals/boards.css";
import { useViewportWidth } from "./visuals/useViewportWidth";
import type { MapMarker } from "./visuals/WorldMap";

const PAGE_LIMIT = 200;

type PlacePage = { items: Entity[]; next_offset: number | null };

function useDelayed(active: boolean, delay: number) {
  const [ready, setReady] = useState(false);
  useEffect(() => {
    if (!active) {
      setReady(false);
      return;
    }
    const timer = window.setTimeout(() => setReady(true), delay);
    return () => window.clearTimeout(timer);
  }, [active, delay]);
  return ready;
}

function placeDefinitions(definitions: Definition[] | undefined) {
  if (!definitions) return [];
  const keyed = definitions.filter((item) => item.key === "location");
  if (keyed.length > 0) return keyed;
  return definitions.filter((item) => item.spec?.label === "地点");
}

function toPage(value: Json | undefined): PlacePage | undefined {
  if (!value) return undefined;
  const items = Array.isArray(value.items) ? (value.items as Entity[]) : [];
  return {
    items,
    next_offset:
      typeof value.next_offset === "number" ? value.next_offset : null,
  };
}

export function MapPage() {
  const { scope } = useWorkspace();
  const width = useViewportWidth();
  const client = useQueryClient();
  const scopeSeen = useRef(scope.id);
  const [kindChoice, setKindChoice] = useState<string>();
  const [qDraft, setQDraft] = useState("");
  const [q, setQ] = useState("");
  const [frame, setFrame] = useState("all");
  const [offset, setOffset] = useState(0);
  const [stableOffset, setStableOffset] = useState(0);
  const [attachmentDraft, setAttachmentDraft] = useState("");
  const [attachmentId, setAttachmentId] = useState("");
  const [basemapUrl, setBasemapUrl] = useState<string>();
  const [basemapNote, setBasemapNote] = useState<string>();
  const [basemapBusy, setBasemapBusy] = useState(false);
  if (scopeSeen.current !== scope.id) {
    scopeSeen.current = scope.id;
    setKindChoice(undefined);
    setQDraft("");
    setQ("");
    setFrame("all");
    setOffset(0);
    setStableOffset(0);
    setAttachmentDraft("");
    setAttachmentId("");
    setBasemapUrl(undefined);
    setBasemapNote(undefined);
  }
  const definitions = useQuery({
    queryKey: ["scope", scope.id, "definitions"],
    queryFn: () => api<Definition[]>(scoped(scope.id, "/definitions")),
    retry: false,
  });
  const places = placeDefinitions(definitions.data);
  const kind =
    kindChoice && places.some((item) => item.key === kindChoice)
      ? kindChoice
      : places[0]?.key;
  const searchKey = [
    "scope",
    scope.id,
    "map-places",
    kind ?? "",
    q,
    offset,
  ] as const;
  const search = useQuery({
    queryKey: searchKey,
    enabled: Boolean(kind),
    retry: false,
    queryFn: () =>
      api<Json>(scoped(scope.id, "/entities/search"), "POST", {
        kind,
        q,
        offset,
        limit: PAGE_LIMIT,
      }),
  });
  useEffect(() => {
    if (search.isSuccess) setStableOffset(offset);
  }, [search.isSuccess, offset]);
  const turning = search.isError && offset !== stableOffset;
  const stableKey = [
    "scope",
    scope.id,
    "map-places",
    kind ?? "",
    q,
    stableOffset,
  ] as const;
  const kept = turning
    ? toPage(client.getQueryData<Json>(stableKey))
    : undefined;
  const page = search.isSuccess ? toPage(search.data) : kept;
  const firstLoad =
    definitions.isPending || (Boolean(kind) && search.isPending && !page);
  const showSkeleton = useDelayed(firstLoad, 200);
  const slow = useDelayed(firstLoad, 10000);
  const failed = (definitions.isError || search.isError) && !page;
  const items = page?.items ?? [];
  const filtered = useMemo(
    () =>
      frame === "all"
        ? items
        : items.filter((item) => item.data?.coordinate?.frame === frame),
    [frame, items],
  );
  const frames = useMemo(() => {
    const found = new Set<string>();
    for (const item of items) {
      const value = item.data?.coordinate?.frame;
      if (typeof value === "string" && value) found.add(value);
    }
    return Array.from(found);
  }, [items]);
  const markers = useMemo(() => {
    const plotted: MapMarker[] = [];
    for (const item of filtered) {
      const read = readCoordinate(item.data?.coordinate);
      if (!read.plot) continue;
      plotted.push({
        id: item.id,
        name: item.name,
        x: read.point.x,
        y: read.point.y,
      });
    }
    return plotted;
  }, [filtered]);
  useEffect(() => {
    if (!attachmentId) {
      setBasemapUrl(undefined);
      setBasemapBusy(false);
      return;
    }
    let active = true;
    let object: string | undefined;
    setBasemapBusy(true);
    setBasemapNote(undefined);
    fetch(`/api/v1/scopes/${scope.id}/attachments/${attachmentId}`, {
      credentials: "same-origin",
    })
      .then((response) => {
        if (!response.ok) throw Error("底图不可访问");
        return response.blob();
      })
      .then((blob) => {
        if (!active) return;
        object = URL.createObjectURL(blob);
        setBasemapUrl(object);
        setBasemapNote(undefined);
      })
      .catch(() => {
        if (!active) return;
        setBasemapUrl(undefined);
        setBasemapNote("底图不可访问");
      })
      .finally(() => {
        if (active) setBasemapBusy(false);
      });
    return () => {
      active = false;
      if (object) URL.revokeObjectURL(object);
    };
  }, [attachmentId, scope.id]);
  function applySearch(value: string) {
    setQ(value);
    setOffset(0);
    setStableOffset(0);
  }
  function applyKind(value: string) {
    setKindChoice(value);
    setOffset(0);
    setStableOffset(0);
    setFrame("all");
  }
  function clearFilters() {
    setQDraft("");
    setQ("");
    setFrame("all");
    setOffset(0);
    setStableOffset(0);
  }
  function loadBasemap() {
    const id = attachmentDraft.trim();
    if (!id) {
      setAttachmentId("");
      setBasemapUrl(undefined);
      setBasemapNote("先填写已经知道的附件编号。页面没有底图目录。");
      return;
    }
    setBasemapNote(undefined);
    setAttachmentId(id);
  }
  const noPlaceType = definitions.isSuccess && places.length === 0;
  const unfilteredEmpty =
    !failed &&
    page != null &&
    items.length === 0 &&
    q === "" &&
    frame === "all";
  const filterEmpty =
    !failed &&
    page != null &&
    filtered.length === 0 &&
    !unfilteredEmpty &&
    !noPlaceType;
  const showEmpty = noPlaceType || unfilteredEmpty;
  const mountCanvas = width > 768 && page != null && !showEmpty && !failed;
  const failureText = definitions.isError
    ? effectDetail(definitions.error)
    : effectDetail(search.error);
  return (
    <div aria-busy={firstLoad || undefined}>
      <PageTitle
        title="地图与地点"
        note="支持虚构坐标与本地底图。标注使用稳定地点身份，未知坐标保持未知。"
      />
      <p className="scope-note" data-component="scope-line">
        {scopeLine(scope.name, scope.kind, scope.version)}
      </p>
      {slow && <p>这一页读得比较久。</p>}
      {showSkeleton && firstLoad && (
        <Skeleton active title={false} paragraph={{ rows: 4 }} />
      )}
      {search.isFetching && page && <p className="rel-caption">正在重新读取</p>}
      {failed && (
        <Alert
          type="error"
          showIcon
          title={failureText}
          action={
            <Button
              onClick={() =>
                definitions.isError ? definitions.refetch() : search.refetch()
              }
            >
              重试
            </Button>
          }
        />
      )}
      {turning && (
        <Alert
          type="error"
          showIcon
          title={effectDetail(search.error)}
          action={
            <Button
              onClick={() => search.refetch()}
              disabled={search.isFetching}
            >
              重试
            </Button>
          }
        />
      )}
      {!definitions.isError && !noPlaceType && kind && (
        <div className="map-filters">
          <Select
            aria-label="地点类型"
            value={kind}
            onChange={applyKind}
            style={{ width: 180 }}
            options={places.map((item) => ({
              value: item.key,
              label: item.spec?.label || item.key,
            }))}
          />
          <Input.Search
            aria-label="按名称筛选地点"
            placeholder="搜索地点名称"
            value={qDraft}
            onChange={(event) => setQDraft(event.target.value)}
            onSearch={applySearch}
            allowClear
            style={{ width: 220 }}
          />
          <Select
            aria-label="坐标系"
            value={frame}
            onChange={setFrame}
            style={{ width: 160 }}
            options={[
              { value: "all", label: "全部" },
              ...frames.map((value) => ({ value, label: value })),
            ]}
          />
          <Input
            aria-label="底图附件编号"
            placeholder="填写附件编号"
            value={attachmentDraft}
            onChange={(event) => setAttachmentDraft(event.target.value)}
            style={{ width: 180 }}
          />
          <Button
            className="hit-44"
            onClick={loadBasemap}
            loading={basemapBusy}
          >
            {basemapBusy ? "正在读取底图" : "使用底图"}
          </Button>
        </div>
      )}
      {basemapNote && <p>{basemapNote}</p>}
      {showEmpty && (
        <NoData
          text="当前范围没有地点"
          action={<Link to="/materials">打开作品资料</Link>}
        />
      )}
      {filterEmpty && (
        <Space orientation="vertical">
          <p>没有符合名称或坐标系的地点</p>
          <Button className="hit-44" onClick={clearFilters}>
            清除筛选
          </Button>
        </Space>
      )}
      {page && !showEmpty && !filterEmpty && (
        <div className="map-split">
          <div>
            {filtered.map((item) => {
              const read = readCoordinate(item.data?.coordinate);
              return (
                <button
                  key={item.id}
                  type="button"
                  className="place-row"
                  data-entity={item.id}
                  data-plot={read.plot ? "1" : "0"}
                >
                  <h3>{item.name}</h3>
                  <span>
                    {read.plot
                      ? `坐标 ${read.point.x}，${read.point.y} · 坐标系 ${read.point.frame} · 已上图`
                      : read.label}
                  </span>
                </button>
              );
            })}
            <p className="rel-caption">
              本页 {items.length}{" "}
              条。没有坐标的地点不会画到图上，也不会画在原点。移动视图不改地理事实。
            </p>
            {items.length === PAGE_LIMIT && page.next_offset != null && (
              <p>本页 200 条，后面还有，当前图不是全部地点</p>
            )}
            {page.next_offset != null && (
              <Button
                className="hit-44"
                disabled={search.isFetching}
                onClick={() => setOffset(page.next_offset as number)}
              >
                {search.isFetching && offset !== stableOffset
                  ? "正在读取下一页"
                  : "下一页"}
              </Button>
            )}
          </div>
          {mountCanvas && (
            <Suspense fallback="加载地图">
              <MapCanvas points={markers} imageUrl={basemapUrl} />
            </Suspense>
          )}
        </div>
      )}
    </div>
  );
}
