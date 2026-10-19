import { Input, Select, Space } from "antd";
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
import { useEffect, useRef, useState } from "react";
import { type Entity } from "../../../shared/api";

export function WorldMap({
  scope,
  entities,
}: {
  scope: string;
  entities: Entity[];
}) {
  const element = useRef<HTMLDivElement>(null),
    [frame, setFrame] = useState("local"),
    [attachment, setAttachment] = useState(""),
    [url, setUrl] = useState<string>();
  const frames = Array.from(
    new Set([
      "local",
      ...entities.map((e) => e.data.coordinate?.frame).filter(Boolean),
    ]),
  );
  useEffect(() => {
    if (!attachment) {
      setUrl(undefined);
      return;
    }
    let object: string | undefined,
      active = true;
    fetch(`/api/v1/scopes/${scope}/attachments/${attachment}`, {
      credentials: "same-origin",
    })
      .then((r) => {
        if (!r.ok) throw Error("底图不可访问");
        return r.blob();
      })
      .then((blob) => {
        if (!active) return;
        object = URL.createObjectURL(blob);
        setUrl(object);
      })
      .catch(() => setUrl(undefined));
    return () => {
      active = false;
      if (object) URL.revokeObjectURL(object);
    };
  }, [attachment, scope]);
  useEffect(() => {
    if (!element.current) return;
    const projection = new Projection({
      code: "NCC:" + frame,
      units: "pixels",
      extent: [0, 0, 2000, 1200],
    });
    const markers = entities
      .filter((e) => e.data.coordinate?.frame === frame)
      .map((e) => {
        const c = e.data.coordinate;
        const f = new Feature({
          geometry: new Point([Number(c.x), Number(c.y)]),
          name: e.name,
        });
        f.setStyle(
          new Style({
            image: new CircleStyle({
              radius: 6,
              fill: new Fill({ color: "#245d4d" }),
              stroke: new Stroke({ color: "#fff", width: 2 }),
            }),
            text: new TextStyle({
              text: e.name,
              offsetY: -16,
              font: "13px sans-serif",
              fill: new Fill({ color: "#213d31" }),
              stroke: new Stroke({ color: "#fff", width: 3 }),
            }),
          }),
        );
        return f;
      });
    const layers: any[] = [];
    if (url)
      layers.push(
        new ImageLayer({
          source: new ImageStatic({
            url,
            projection,
            imageExtent: [0, 0, 2000, 1200],
          }),
        }),
      );
    layers.push(
      new VectorLayer({ source: new VectorSource({ features: markers }) }),
    );
    const map = new Map({
      target: element.current,
      layers,
      view: new View({
        projection,
        center: [1000, 600],
        zoom: 1,
        minZoom: -2,
        maxZoom: 8,
      }),
    });
    map
      .getView()
      .fit([0, 0, 2000, 1200], { size: [900, 500], padding: [30, 30, 30, 30] });
    return () => map.setTarget(undefined);
  }, [entities, frame, url]);
  return (
    <>
      <Space wrap style={{ marginBottom: 16 }}>
        <Select
          aria-label="地图坐标系"
          value={frame}
          onChange={setFrame}
          style={{ width: 200 }}
          options={frames.map((value) => ({ value, label: value }))}
        />
        <Input.Search
          placeholder="可访问的底图附件ID（可选）"
          style={{ width: 360 }}
          onSearch={setAttachment}
          enterButton="加载底图"
        />
      </Space>
      <div
        ref={element}
        className="world-map"
        aria-label="虚构地图与地点标注"
      />
    </>
  );
}
