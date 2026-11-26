import Feature from "ol/Feature";
import Map from "ol/Map";
import View from "ol/View";
import Point from "ol/geom/Point";
import ImageLayer from "ol/layer/Image";
import VectorLayer from "ol/layer/Vector";
import "ol/ol.css";
import Projection from "ol/proj/Projection";
import ImageStatic from "ol/source/ImageStatic";
import VectorSource from "ol/source/Vector";
import {
  Circle as CircleStyle,
  Fill,
  Stroke,
  Style,
  Text as TextStyle,
} from "ol/style";
import { useEffect, useRef } from "react";

export type MapMarker = { id: string; name: string; x: string; y: string };

function extentOf(points: MapMarker[]): [number, number, number, number] {
  if (points.length === 0) return [0, 0, 2000, 1200];
  let minX = Number(points[0].x);
  let maxX = minX;
  let minY = Number(points[0].y);
  let maxY = minY;
  for (const point of points) {
    const x = Number(point.x);
    const y = Number(point.y);
    minX = Math.min(minX, x);
    maxX = Math.max(maxX, x);
    minY = Math.min(minY, y);
    maxY = Math.max(maxY, y);
  }
  if (minX === maxX) {
    minX -= 50;
    maxX += 50;
  }
  if (minY === maxY) {
    minY -= 50;
    maxY += 50;
  }
  return [minX, minY, maxX, maxY];
}

function markerStyle(name: string, active: boolean, tone: string) {
  return new Style({
    image: new CircleStyle({
      radius: active ? 9 : 6,
      fill: new Fill({ color: active ? "#245d4d" : tone }),
      stroke: new Stroke({
        color: active ? "#f3e6bd" : "#ffffff",
        width: active ? 3 : 2,
      }),
    }),
    text: new TextStyle({
      text: name,
      offsetY: active ? -19 : -16,
      font: active ? "600 13px sans-serif" : "13px sans-serif",
      fill: new Fill({ color: tone }),
      stroke: new Stroke({ color: "#ffffff", width: 3 }),
    }),
  });
}

export function WorldMap({
  points,
  imageUrl,
  focusedId,
  onSelectMarker,
}: {
  points: MapMarker[];
  imageUrl?: string;
  focusedId?: string;
  onSelectMarker?: (id: string) => void;
}) {
  const element = useRef<HTMLDivElement>(null);
  const mapRef = useRef<Map | null>(null);
  const sourceRef = useRef<VectorSource | null>(null);
  const onSelectRef = useRef(onSelectMarker);
  onSelectRef.current = onSelectMarker;

  useEffect(() => {
    const host = element.current;
    if (!host) return;
    const tone = getComputedStyle(host).color || "#24362d";
    const extent = extentOf(points);
    const projection = new Projection({
      code: "NCC:places",
      units: "pixels",
      extent,
    });
    const features = points.map((point) => {
      const feature = new Feature({
        geometry: new Point([Number(point.x), Number(point.y)]),
        name: point.name,
      });
      feature.setId(point.id);
      feature.setStyle(markerStyle(point.name, point.id === focusedId, tone));
      return feature;
    });
    const vectorSource = new VectorSource({ features });
    sourceRef.current = vectorSource;
    const layers = [];
    if (imageUrl) {
      layers.push(
        new ImageLayer({
          source: new ImageStatic({
            url: imageUrl,
            projection,
            imageExtent: extent,
          }),
        }),
      );
    }
    layers.push(new VectorLayer({ source: vectorSource }));
    const map = new Map({
      target: host,
      layers,
      view: new View({
        projection,
        center: [(extent[0] + extent[2]) / 2, (extent[1] + extent[3]) / 2],
        zoom: 1,
        minZoom: -2,
        maxZoom: 8,
      }),
    });
    mapRef.current = map;
    map.getView().fit(extent, { padding: [36, 36, 36, 36] });
    map.on("singleclick", (evt) => {
      map.forEachFeatureAtPixel(evt.pixel, (feat) => {
        const id = feat.getId();
        if (id != null && onSelectRef.current) {
          onSelectRef.current(String(id));
          return true;
        }
        return false;
      });
    });
    return () => {
      mapRef.current = null;
      sourceRef.current = null;
      map.setTarget(undefined);
    };
  }, [points, imageUrl]);

  useEffect(() => {
    const map = mapRef.current;
    const source = sourceRef.current;
    const host = element.current;
    if (!map || !source || !host) return;
    const tone = getComputedStyle(host).color || "#24362d";
    for (const point of points) {
      const feature = source.getFeatureById(point.id);
      if (feature) {
        feature.setStyle(markerStyle(point.name, point.id === focusedId, tone));
      }
    }
    if (focusedId) {
      const target = points.find((p) => p.id === focusedId);
      if (target) {
        map.getView().setCenter([Number(target.x), Number(target.y)]);
      }
    }
  }, [focusedId, points]);

  return (
    <div className="map-board">
      <div
        ref={element}
        className="world-map"
        data-component="map-board"
        data-marker-count={points.length}
        data-marker-ids={points.map((point) => point.id).join(" ")}
        aria-label="只画出有坐标的地点"
      />
      <ol className="marker-ledger">
        {points.map((point) => (
          <li
            key={point.id}
            data-marker={point.id}
            data-x={point.x}
            data-y={point.y}
          />
        ))}
      </ol>
    </div>
  );
}
