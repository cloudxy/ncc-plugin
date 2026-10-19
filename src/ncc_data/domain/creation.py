"""Canonical content-scheme metadata for workers and management clients."""

REVISION_SCHEMES = {
    "chapter": "P1",
    "章节": "P1",
    "outline": "P2",
    "scene": "P2",
    "volume": "P2",
    "source": "P4",
    "legacy-file": "P4",
}
SCHEME_LABELS = {
    "P1": "正文章节",
    "P2": "大纲与场景",
    "P3": "人物与世界设定",
    "P4": "资料整理",
    "P5": "修改与更新",
}


def creation_scheme(payload):
    if payload["scheme"] != "P5":
        return payload["scheme"]
    return payload.get("content_scheme") or REVISION_SCHEMES.get(payload["kind"], "P3")
