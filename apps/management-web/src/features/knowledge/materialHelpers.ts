import type { Definition, Json } from "../../shared/api";
import type { CodexGroup } from "../../shared/studioApi";

export const FALLBACK_GROUPS: CodexGroup[] = [
  {
    id: "characters",
    label: "人物与角色职业",
    description: "",
    kinds: [
      "人物",
      "身份",
      "法师",
      "人物弧",
      "动机",
      "秘密",
      "血脉",
      "体质",
      "语言风格",
      "character",
    ],
    recommended_fields: [
      "motivation",
      "psychology",
      "arc_type",
      "voice",
      "factions",
      "pov",
    ],
  },
  {
    id: "beings",
    label: "种族与异界生物",
    description: "",
    kinds: [
      "种族",
      "妖兽",
      "魔兽",
      "异世界生物",
      "亡灵",
      "鬼",
      "魔",
      "异族人",
      "神兽",
      "灵宠",
      "妖",
      "兽",
      "精怪",
    ],
    recommended_fields: ["habitat", "limitations", "factions", "description"],
  },
  {
    id: "techniques",
    label: "功法技能与特效",
    description: "",
    kinds: [
      "功法",
      "技能",
      "特效",
      "法术",
      "神通",
      "阵法",
      "符箓",
      "境界",
      "招式",
    ],
    recommended_fields: [
      "limitations",
      "side_effects",
      "usage_guide",
      "description",
    ],
  },
  {
    id: "artifacts",
    label: "丹药武器与器物",
    description: "",
    kinds: ["丹药", "现代武器", "法宝", "武器", "道具", "异火", "配方", "丹方"],
    recommended_fields: ["limitations", "side_effects", "cost", "usage_guide"],
  },
  {
    id: "places",
    label: "场景地图与都市舞台",
    description: "",
    kinds: [
      "场景",
      "地图",
      "都市",
      "城池",
      "秘境",
      "拍卖会",
      "拍卖行",
      "战场",
      "scene",
      "location",
    ],
    recommended_fields: ["description", "plotline", "hook"],
  },
  {
    id: "orders",
    label: "组织势力与世界规则",
    description: "",
    kinds: ["宗门", "帝国", "商会", "法则", "制度", "货币", "家族", "王朝"],
    recommended_fields: ["factions", "limitations", "description"],
  },
];

export const CARD_LABELS: Record<string, string> = {
  motivation: "动机",
  psychology: "心理与伤口",
  arc_type: "人物弧光",
  voice: "语言风格",
  factions: "阵营",
  pov: "视角人物",
  habitat: "栖息地",
  limitations: "限制与代价",
  side_effects: "副作用",
  usage_guide: "用法禁忌",
  description: "摘要",
  cost: "代价",
  plotline: "剧情线",
  hook: "追读钩",
};

export function viewEntries(config: Json | undefined): [string, Json][] {
  const views = config?.views;
  if (!views || typeof views !== "object" || Array.isArray(views)) return [];
  return Object.entries(views).filter(
    (entry): entry is [string, Json] =>
      !!entry[1] && typeof entry[1] === "object" && !Array.isArray(entry[1]),
  );
}

export function fieldText(value: unknown): string {
  if (value === undefined || value === null || value === "") return "";
  if (typeof value === "string" || typeof value === "number")
    return String(value);
  if (typeof value === "boolean") return value ? "是" : "否";
  if (Array.isArray(value))
    return value
      .map((item) => fieldText(item))
      .filter(Boolean)
      .join("、");
  return "";
}

export function resolveKindLabel(
  defs: Definition[] | undefined,
  value: string,
): string {
  const found = defs?.find((item) => item.key === value);
  return found?.spec.label || value;
}

export function resolveFieldLabel(
  defs: Definition[] | undefined,
  key: string,
): string {
  if (CARD_LABELS[key]) return CARD_LABELS[key];
  for (const item of defs || []) {
    const rule = item.spec.properties?.[key];
    if (rule?.label) return String(rule.label);
  }
  return key;
}
