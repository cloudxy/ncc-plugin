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
    minX -= 1;
    maxX += 1;
  }
  if (minY === maxY) {
    minY -= 1;
    maxY += 1;
  }
  return [minX, minY, maxX, maxY];
}

export function WorldMap({
  points,
  imageUrl,
}: {
  points: MapMarker[];
  imageUrl?: string;
}) {
  const element = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const host = element.current;
    if (!host) return;
    const tone = getComputedStyle(host).color || "CanvasText";
    const extent = extentOf(points);
    const projection = new Projection({
      code: "NCC:places",
      units: "pixels",
      extent,
    });
    const markers = points.map((point) => {
      const feature = new Feature({
        geometry: new Point([Number(point.x), Number(point.y)]),
        name: point.name,
      });
      feature.setId(point.id);
      feature.setStyle(
        new Style({
          image: new CircleStyle({
            radius: 6,
            fill: new Fill({ color: tone }),
            stroke: new Stroke({ color: "Canvas", width: 2 }),
          }),
          text: new TextStyle({
            text: point.name,
            offsetY: -16,
            font: "13px sans-serif",
            fill: new Fill({ color: tone }),
            stroke: new Stroke({ color: "Canvas", width: 3 }),
          }),
        }),
      );
      return feature;
    });
    const layers = [];
    if (imageUrl)
      layers.push(
        new ImageLayer({
          source: new ImageStatic({
            url: imageUrl,
            projection,
            imageExtent: extent,
          }),
        }),
      );
    layers.push(
      new VectorLayer({ source: new VectorSource({ features: markers }) }),
    );
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
    map.getView().fit(extent, { padding: [30, 30, 30, 30] });
    return () => map.setTarget(undefined);
  }, [points, imageUrl]);
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
      <p className="rel-caption">移动视图不改地理事实。</p>
    </div>
  );
}
