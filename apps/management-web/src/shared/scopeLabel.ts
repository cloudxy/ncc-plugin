const KIND_LABEL = {
  book: "书项目",
  author: "作者资料库",
  universe: "共享宇宙",
  series: "系列",
  research: "拆书研究",
  branch: "IF分支",
} as const;

export const SCOPE_KINDS = Object.keys(
  KIND_LABEL,
) as (keyof typeof KIND_LABEL)[];

export function kindLabel(kind: string) {
  return Object.prototype.hasOwnProperty.call(KIND_LABEL, kind)
    ? KIND_LABEL[kind as keyof typeof KIND_LABEL]
    : kind;
}

export function scopeTag(kind: string, version: number) {
  return `${kindLabel(kind)} · ${version}`;
}

export function scopeLine(name: string, kind: string, version: number) {
  return `${name} · ${kindLabel(kind)} · 记录版本 ${version}`;
}
