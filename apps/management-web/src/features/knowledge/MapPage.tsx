import { UploadOutlined } from "@ant-design/icons";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Alert,
  App,
  Button,
  Input,
  Select,
  Skeleton,
  Space,
  Upload,
} from "antd";
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
import { queryKeys } from "../../shared/queryKeys";
import { scopeLine } from "../../shared/scopeLabel";
import {
  fetchStudioOverview,
  saveStudioMapConfig,
} from "../../shared/studioApi";
import { useDelayed } from "../../shared/useDelayed";
import { useWorkspace } from "../../shared/WorkspaceContext";
import { effectDetail } from "../creation/effectDetail";
import { EntityDrawer } from "./components/EntityDrawer";
import { MapCanvas } from "./components/KnowledgeVisuals";
import { readCoordinate } from "./coordinates";
import "./visuals/boards.css";
import { useViewportWidth } from "./visuals/useViewportWidth";
import type { MapMarker } from "./visuals/WorldMap";

const PAGE_LIMIT = 200;
const SAFE_RASTER_TYPES = new Set([
  "image/png",
  "image/jpeg",
  "image/webp",
  "image/gif",
]);

type PlacePage = { items: Entity[]; next_offset: number | null };

function isRasterAttachment(row: Json): boolean {
  if (
    typeof row.media_type === "string" &&
    SAFE_RASTER_TYPES.has(row.media_type)
  ) {
    return true;
  }
  const lower = String(row.name || "").toLowerCase();
  return (
    lower.endsWith(".png") ||
    lower.endsWith(".jpg") ||
    lower.endsWith(".jpeg") ||
    lower.endsWith(".webp") ||
    lower.endsWith(".gif")
  );
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
  const { message } = App.useApp();
  const width = useViewportWidth();
  const client = useQueryClient();
  const scopeSeen = useRef(scope.id);
  const [kindChoice, setKindChoice] = useState<string>();
  const [qDraft, setQDraft] = useState("");
  const [q, setQ] = useState("");
  const [frame, setFrame] = useState("all");
  const [offset, setOffset] = useState(0);
  const [stableOffset, setStableOffset] = useState(0);
  const [manualBasemapId, setManualBasemapId] = useState<string | undefined>();
  const [basemapUrl, setBasemapUrl] = useState<string>();
  const [basemapNote, setBasemapNote] = useState<string>();
  const [basemapBusy, setBasemapBusy] = useState(false);
  const [uploadingBasemap, setUploadingBasemap] = useState(false);
  const [savingDefault, setSavingDefault] = useState(false);
  const [focusedPlaceId, setFocusedPlaceId] = useState<string>();
  const [drawerId, setDrawerId] = useState<string>();

  const canEdit = scope.actions.includes("edit");

  if (scopeSeen.current !== scope.id) {
    scopeSeen.current = scope.id;
    setKindChoice(undefined);
    setQDraft("");
    setQ("");
    setFrame("all");
    setOffset(0);
    setStableOffset(0);
    setManualBasemapId(undefined);
    setBasemapUrl(undefined);
    setBasemapNote(undefined);
    setFocusedPlaceId(undefined);
    setDrawerId(undefined);
  }

  const definitions = useQuery({
    queryKey: queryKeys.definitions(scope.id),
    queryFn: () => api<Definition[]>(scoped(scope.id, "/definitions")),
    retry: false,
  });

  const overview = useQuery({
    queryKey: queryKeys.studioOverview(scope.id),
    queryFn: () => fetchStudioOverview(scope.id),
  });

  const attachments = useQuery({
    queryKey: queryKeys.attachments(scope.id, "source"),
    queryFn: () => api<Json[]>(scoped(scope.id, "/attachments?purpose=source")),
  });

  const savedDefaultBasemapId =
    overview.data?.map_config?.basemap_attachment_id || "";
  const activeAttachmentId =
    manualBasemapId !== undefined ? manualBasemapId : savedDefaultBasemapId;

  const imageAttachments = useMemo(
    () => (attachments.data || []).filter(isRasterAttachment),
    [attachments.data],
  );

  const basemapOptions = useMemo(() => {
    const opts = imageAttachments.map((item) => ({
      value: String(item.id),
      label: `${item.name}${item.id === savedDefaultBasemapId ? "（默认）" : ""}`,
    }));
    if (
      activeAttachmentId &&
      !opts.some((item) => item.value === activeAttachmentId)
    ) {
      opts.unshift({
        value: activeAttachmentId,
        label: `底图附件 ${activeAttachmentId.slice(0, 8)}…`,
      });
    }
    return opts;
  }, [imageAttachments, activeAttachmentId, savedDefaultBasemapId]);

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
    if (!activeAttachmentId) {
      setBasemapUrl(undefined);
      setBasemapBusy(false);
      return;
    }
    let active = true;
    let object: string | undefined;
    setBasemapBusy(true);
    setBasemapNote(undefined);
    fetch(
      `/api/v1/scopes/${scope.id}/attachments/${encodeURIComponent(activeAttachmentId)}?inline=true`,
      {
        credentials: "same-origin",
      },
    )
      .then((response) => {
        if (!response.ok) throw Error("底图不可访问");
        const contentType = response.headers.get("content-type") || "";
        if (!contentType.startsWith("image/")) {
          throw Error("所选附件不是受支持的位图格式（支持 PNG/JPG/WebP/GIF）");
        }
        return response.blob();
      })
      .then((blob) => {
        if (!active) return;
        object = URL.createObjectURL(blob);
        setBasemapUrl(object);
        setBasemapNote(undefined);
      })
      .catch((err) => {
        if (!active) return;
        setBasemapUrl(undefined);
        setBasemapNote((err as Error).message || "底图不可访问");
      })
      .finally(() => {
        if (active) setBasemapBusy(false);
      });
    return () => {
      active = false;
      if (object) URL.revokeObjectURL(object);
    };
  }, [activeAttachmentId, scope.id]);

  async function handleUploadBasemap(file: File) {
    if (!canEdit) return false;
    setUploadingBasemap(true);
    setBasemapNote(undefined);
    try {
      const body = new FormData();
      body.append("file", file);
      const uploaded = await api<Json>(
        scoped(scope.id, "/attachments"),
        "POST",
        body,
      );
      const newId = String(uploaded.id);
      setManualBasemapId(newId);
      await saveStudioMapConfig(scope.id, newId);
      await Promise.all([attachments.refetch(), overview.refetch()]);
      message.success("底图已上传并设为当前作品默认底图");
    } catch (err) {
      message.error(effectDetail(err));
    } finally {
      setUploadingBasemap(false);
    }
    return false;
  }

  async function persistDefaultBasemap(targetId: string | null) {
    if (!canEdit) return;
    setSavingDefault(true);
    try {
      await saveStudioMapConfig(scope.id, targetId);
      await overview.refetch();
      message.success(targetId ? "已保存为默认地图底图" : "已清除默认地图底图");
    } catch (err) {
      message.error(effectDetail(err));
    } finally {
      setSavingDefault(false);
    }
  }

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
        note="支持虚构坐标与安全位图底图。点击地点可在地图居中聚焦，或打开资料抽屉补充坐标。"
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
            style={{ width: 160 }}
            options={places.map((item) => ({
              value: item.key,
              label: item.spec?.label || item.key,
            }))}
          />
          <Input.Search
            aria-label="按名称筛选地点"
            placeholder="搜索地点名称"
            value={qDraft}
            onChange={(event) => {
              setQDraft(event.target.value);
              if (!event.target.value) applySearch("");
            }}
            onSearch={applySearch}
            allowClear
            style={{ width: 200 }}
          />
          <Select
            aria-label="坐标系"
            value={frame}
            onChange={setFrame}
            style={{ width: 150 }}
            options={[
              { value: "all", label: "全部坐标系" },
              ...frames.map((value) => ({ value, label: value })),
            ]}
          />
          <Select
            aria-label="选择底图附件"
            allowClear
            placeholder="选择已有图片底图"
            loading={attachments.isPending || basemapBusy}
            value={activeAttachmentId || undefined}
            style={{ width: 220 }}
            options={basemapOptions}
            onChange={(val) => {
              setBasemapNote(undefined);
              setManualBasemapId(val || "");
            }}
          />
          <Upload
            accept=".png,.jpg,.jpeg,.webp,.gif,image/png,image/jpeg,image/webp,image/gif"
            showUploadList={false}
            beforeUpload={handleUploadBasemap}
          >
            <Button
              icon={<UploadOutlined />}
              disabled={!canEdit}
              loading={uploadingBasemap}
            >
              上传图片底图
            </Button>
          </Upload>
          {canEdit && activeAttachmentId !== savedDefaultBasemapId && (
            <Button
              loading={savingDefault}
              onClick={() =>
                void persistDefaultBasemap(activeAttachmentId || null)
              }
            >
              {activeAttachmentId ? "设为默认底图" : "清除默认底图"}
            </Button>
          )}
        </div>
      )}
      {basemapNote && <Alert type="warning" showIcon title={basemapNote} />}
      {showEmpty && (
        <NoData
          text="当前范围没有地点"
          action={<Link to="/materials">打开作品资料新建地点</Link>}
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
              const isFocused = focusedPlaceId === item.id;
              return (
                <div
                  key={item.id}
                  className={isFocused ? "place-card is-focused" : "place-card"}
                >
                  <button
                    type="button"
                    className="place-row"
                    data-entity={item.id}
                    data-plot={read.plot ? "1" : "0"}
                    onClick={() => {
                      if (read.plot) {
                        setFocusedPlaceId(item.id);
                      } else {
                        setDrawerId(item.id);
                      }
                    }}
                  >
                    <h3>{item.name}</h3>
                    <span>
                      {read.plot
                        ? `坐标 ${read.point.x}，${read.point.y} · 坐标系 ${read.point.frame} · 点击在地图居中`
                        : `${read.label} · 点击补充坐标`}
                    </span>
                  </button>
                  <Button
                    size="small"
                    type="link"
                    onClick={() => setDrawerId(item.id)}
                  >
                    {read.plot ? "编辑坐标" : "补充坐标"}
                  </Button>
                </div>
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
              <MapCanvas
                points={markers}
                imageUrl={basemapUrl}
                focusedId={focusedPlaceId}
                onSelectMarker={(id) => setFocusedPlaceId(id)}
              />
            </Suspense>
          )}
        </div>
      )}
      <EntityDrawer
        id={drawerId}
        onClose={() => {
          setDrawerId(undefined);
          search.refetch();
        }}
      />
    </div>
  );
}
