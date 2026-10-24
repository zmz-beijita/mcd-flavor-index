#!/usr/bin/env python3
"""生成首页双榜数据。

真香榜：data_ugc.json 里 6 个有真实评价的商品（评分排序）
人气榜：data/menu_full.json 里门店全部在售商品，按官方信号标签排序

输出：data/home.json
"""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 官方信号标签（麦当劳自己打的销量/推荐信号）
SIGNAL_TAGS = [
    ("人气热卖", 100), ("人气经典", 92), ("人气", 88), ("爆款", 90),
    ("粉丝之选", 86), ("上新", 80), ("新升级", 70), ("限时特惠", 76),
    ("限定特惠", 74), ("经典精选", 72), ("超值", 66),
    ("超值百种组合随心配", 64), ("万种组合", 60), ("随心拼", 58),
]
# 这些是分类/规格标签，不是信号
STRUCTURE_TAGS = {
    "单品", "套餐", "小食", "冷饮", "热饮", "蘸酱", "蘸酱炸鸡", "新升级",
    "小食拼盘", "小食甜品\n/其他", "鸡肉汉堡\n/卷", "巨无霸\n牛鱼肉堡",
    "安格斯MAX\n厚牛堡", "随心配\n1+1", "500\n大卡套餐", "大堡口福\n单人餐",
    "精选单人餐", "精选单人餐\n/单人餐", "人气热卖", "麦咖啡™咖啡", "鲜萃咖啡",
    "麦金卡", "特惠", "经典精选",
}
# 冰量/甜度选项不是配料
ICE_ONLY = {"标准", "去冰", "多冰", "少冰", "不加", "加", "换燕麦奶", "奶油球", "白砂糖"}


def load(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return json.load(f)


def signal_score(tags):
    s = 0
    for t in tags:
        for name, w in SIGNAL_TAGS:
            if t == name:
                s = max(s, w)
    return s


def flavor_tags(tags):
    """只保留描述风味/特征的官方标签，去掉分类与规格标签。"""
    out = []
    for t in tags:
        if t in STRUCTURE_TAGS or t in SIGNAL_TAGS:
            continue
        if re.fullmatch(r"[a-zA-Z\s™®]+", t):   # 纯英文标签（如 麦咖啡™咖啡）
            continue
        out.append(t)
    return out


def ingredients(ings):
    """去掉冰量/甜度这类选项，只留真正的配料。"""
    return [x for x in ings if x not in ICE_ONLY]


def main():
    ugc = load("data_ugc.json")
    menu = load("data/menu_full.json")

    by_name = {it["name"]: it for it in ugc["items"]}

    # ---------- 真香榜 ----------
    truth = []
    for it in ugc["items"]:
        scores = [u["score"] for u in it["ugc"]]
        n = len(scores)
        avg = sum(scores) / n
        m = menu.get(it["name"], {})
        truth.append({
            "name": it["name"],
            "avg": round(avg, 1),
            "min": min(scores), "max": max(scores), "spread": max(scores) - min(scores),
            "n": n,
            "cat": it.get("cat", "在售"),
            "price": it.get("official_price_yuan"),
            "price_note": it.get("price_note"),
            "official_tags": it.get("official_tags", []),
            "flavor_tags": flavor_tags(m.get("tags", []) or it.get("official_tags", [])),
            "ingredients": ingredients(m.get("ings", [])),
            "official_desc": (m.get("official_desc") or {}).get("text"),
            "real": it.get("real", []),
            "ugc": it["ugc"],
            "has_review": True,
        })
    truth.sort(key=lambda x: (-x["avg"], -x["n"]))

    # ---------- 人气榜（全部在售） ----------
    hot = []
    for nm, m in menu.items():
        t = by_name.get(nm)
        sig = signal_score(m.get("tags", []))
        fl = flavor_tags(m.get("tags", []))
        ings = ingredients(m.get("ings", []))
        d = m.get("official_desc") or {}
        item = {
            "name": nm,
            "cat": (m.get("cats") or ["在售"])[0].replace("\n", ""),
            "price": m.get("price"),
            "signal": sig,
            "flavor_tags": fl,
            "ingredients": ings,
            "official_desc": d.get("text"),
            "has_review": bool(t),
            "avg": round(sum(u["score"] for u in t["ugc"]) / len(t["ugc"]), 1) if t else None,
            "n": len(t["ugc"]) if t else 0,
        }
        hot.append(item)
    # 有信号的在前（信号分降序），无信号的按名称稳定排序放后
    hot.sort(key=lambda x: (-x["signal"], -x["avg"] if x["avg"] else 0, x["name"]))

    out = {
        "collected_at": ugc.get("collected_at", "2026-10-25"),
        "store": "麦当劳上海黄浦华旭国际大厦餐厅 (1450713)",
        "truth": truth,
        "hot": hot,
    }
    path = os.path.join(ROOT, "data", "home.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    print(f"真香榜 {len(truth)} 个商品（有真实评价）")
    print(f"人气榜 {len(hot)} 个商品（门店全部在售）")
    print(f"  有官方风味标签: {sum(1 for x in hot if x['flavor_tags'])}")
    print(f"  有官方配料清单: {sum(1 for x in hot if x['ingredients'])}")
    print(f"  有官方描述文案: {sum(1 for x in hot if x['official_desc'])}")
    print(f"  带销量信号标签: {sum(1 for x in hot if x['signal'])}")
    print(f"\n→ {path}")


if __name__ == "__main__":
    main()
