#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把网页版数据同步到微信小程序的预置数据文件。

小程序与网页共用同一套真香指数口径，两边的评价、榜单、核价必须一致，
否则「网页说 49 篇、小程序说 27 篇」会被评委一眼看穿。

用法：
    python scripts/sync_miniprogram.py
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return json.load(f)


def main():
    home = load("data/home.json")
    img_map = load("data/img_map.json")
    truth = home.get("truth", [])
    hot = home.get("hot", [])

    def local_img(name):
        """本地图片路径（小程序用 /assets/xxx）。"""
        rel = img_map.get(name)
        return ("/assets/" + os.path.basename(rel)) if rel else ""

    # 小程序 items 结构与网页真香榜一致，去掉网页专用字段
    items = []
    for t in truth:
        items.append({
            "name": t["name"],
            "cat": t.get("cat", "在售"),
            "avg": t.get("avg"),
            "min": t.get("min"),
            "max": t.get("max"),
            "spread": t.get("spread", 0),
            "n": t.get("n", 0),
            "price": t.get("price"),
            "price_note": t.get("price_note"),
            "official_tags": t.get("official_tags", []),
            "flavor_tags": t.get("flavor_tags", []),
            "ingredients": t.get("ingredients", []),
            "official_desc": t.get("official_desc"),
            "official_rounds": t.get("official_rounds", []),
            "image": t.get("image", ""),
            "local_image": local_img(t["name"]),
            "real": t.get("real", []),
            "ugc": t.get("ugc", []),
            "has_review": True,
        })

    # 小程序 hot 与网页人气榜一致
    mp_hot = []
    for h in hot:
        mp_hot.append({
            "name": h["name"],
            "cat": h.get("cat", "在售"),
            "price": h.get("price"),
            "signal": h.get("signal", 0),
            "flavor_tags": h.get("flavor_tags", []),
            "ingredients": h.get("ingredients", []),
            "image": h.get("image", ""),
            "local_image": local_img(h["name"]),
            "official_desc": h.get("official_desc"),
            "official_rounds": h.get("official_rounds", []),
            "official_desc_date": h.get("official_desc_date"),
            "has_review": h.get("has_review", False),
            "avg": h.get("avg"),
            "n": h.get("n", 0),
            "min": h.get("min"),
            "max": h.get("max"),
            "spread": h.get("spread", 0),
        })

    out = {
        "collected_at": home.get("collected_at", "2026-10-25"),
        "store": home.get("store", ""),
        "items": items,
        "hot": mp_hot,
    }

    path = os.path.join(ROOT, "miniprogram", "data", "flavor.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    n_ugc = sum(len(i["ugc"]) for i in items)
    print(f"真香榜 {len(items)} 个商品 / {n_ugc} 篇评价")
    print(f"人气榜 {len(mp_hot)} 个商品")
    print(f"→ {path}")


if __name__ == "__main__":
    main()
