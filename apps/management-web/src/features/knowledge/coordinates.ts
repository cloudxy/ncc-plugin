const DECIMAL = /^-?\d+(\.\d+)?$/;

export type PlotPoint = { x: string; y: string; frame: string };

export type CoordinateRead =
  { plot: true; point: PlotPoint } | { plot: false; label: string };

/** Finite decimal string. Missing, empty, null, and forms such as 1e2 are not decimals. */
export function isFiniteDecimalString(value: unknown): value is string {
  if (typeof value !== "string") return false;
  if (!DECIMAL.test(value)) return false;
  return Number.isFinite(Number(value));
}

function missingLabel(coordinate: Record<string, unknown>): string | null {
  const missing = (["x", "y", "frame"] as const).filter((key) => {
    const value = coordinate[key];
    return value === undefined || value === null || value === "";
  });
  if (missing.length === 0) return null;
  if (missing.length === 3) return "未知坐标 · 留在列表 · 未上图";
  return `不能上图 · 缺 ${missing[0]} · 未上图`;
}

/**
 * Plot only when x and y are finite decimal strings and frame is a non-empty name.
 * Frame stays a coordinate-system name: the accepted row uses "local", which is not a decimal.
 * Never pass a missing value through Number(); Number(null) is 0 and would land on the origin.
 */
export function readCoordinate(coordinate: unknown): CoordinateRead {
  if (coordinate == null || coordinate === "")
    return { plot: false, label: "未知坐标 · 留在列表 · 未上图" };
  if (typeof coordinate !== "object")
    return { plot: false, label: "未知坐标 · 留在列表 · 未上图" };
  const raw = coordinate as Record<string, unknown>;
  const missing = missingLabel(raw);
  if (missing) return { plot: false, label: missing };
  if (
    typeof raw.frame !== "string" ||
    !isFiniteDecimalString(raw.x) ||
    !isFiniteDecimalString(raw.y)
  )
    return { plot: false, label: "不能上图 · 未上图" };
  return { plot: true, point: { x: raw.x, y: raw.y, frame: raw.frame } };
}
