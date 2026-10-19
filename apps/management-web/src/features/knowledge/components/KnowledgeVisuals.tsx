import { lazy } from "react";
export const Graph = lazy(() =>
  import("../visuals/GraphCanvas").then((x) => ({ default: x.GraphCanvas })),
);
export const MapCanvas = lazy(() =>
  import("../visuals/WorldMap").then((x) => ({ default: x.WorldMap })),
);
