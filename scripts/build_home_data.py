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
    ("人气产品", 100), ("人气热卖", 100), ("人气经典", 94), ("人气", 92),
    ("爆款", 90), ("粉丝之选", 88), ("爆款推荐", 88),
    ("上新", 82), ("限时特惠", 78), ("限定特惠", 76), ("特惠", 74),
    ("新升级", 72), ("经典精选", 72), ("超值", 68),
    ("超值百种组合随心配", 66), ("万种组合", 62), ("随心拼", 60),
    ("第二份半价", 58), ("第二份优惠", 58), ("人气新品", 82),
    ("麦金卡专享", 56), ("早餐卡专享价", 52),
]

# 分类优先级：用户真正会点的品类排在前面
CATEGORY_RANK = [
    # 0 主食（汉堡 / 堡 / 牛排类）
    ("汉堡", 0), ("堡", 0), ("牛排", 0), ("双层", 0), ("吉士", 0),
    ("麦满分", 0), ("猪柳", 0), ("鸡腿", 0), ("鸡排", 0), ("鳕鱼", 0),
    ("安格斯", 0), ("巨无霸", 0), ("牛肉", 0), ("厚松饼", 1),
    ("单人餐", 1), ("套餐", 1), ("粥", 1), ("卷", 1), ("麦香", 1),
    # 2 小食 / 炸鸡 / 甜品
    ("小食", 2), ("炸鸡", 2), ("鸡块", 2), ("薯条", 2), ("甜品", 2),
    ("派", 2), ("冰淇淋", 2), ("麦旋风", 2), ("新地", 2), ("热饮", 3),
    # 3 饮品 / 咖啡
    ("饮品", 3), ("咖啡", 3), ("奶铁", 3), ("美式", 3), ("红茶", 3),
    ("果汁", 3), ("奶昔", 3), ("可乐", 3), ("雪碧", 3), ("怡泉", 3),
    # 4 组合 / 多人
    ("随心配", 4), ("拼盘", 4), ("多人", 4), ("分享", 4), ("组合", 4),
    ("欢乐", 4), ("亲子", 4), ("派对", 4), ("全家", 4),
    # 9 周边
    ("周边", 9), ("帽", 9), ("丝巾", 9), ("徽章", 9), ("玩具", 9),
    ("周边系列", 9), ("搪胶", 9), ("水手", 9),
]
# 这些是分类/规格标签，不是信号
STRUCTURE_TAGS = {
    "单品", "套餐", "小食", "冷饮", "热饮", "蘸酱", "蘸酱炸鸡", "新升级",
    "小食拼盘", "小食甜品\n/其他", "鸡肉汉堡\n/卷", "巨无霸\n牛鱼肉堡",
    "安格斯MAX\n厚牛堡", "随心配\n1+1", "500\n大卡套餐", "大堡口福\n单人餐",
    "精选单人餐", "精选单人餐\n/单人餐", "人气热卖", "麦咖啡™咖啡", "鲜萃咖啡",
    "麦金卡", "特惠", "经典精选", "人气产品", "人气", "人气经典", "人气热卖",
    "爆款", "上新", "限时特惠", "限定特惠", "粉丝之选", "经典精选", "超值",
    "麦金卡专享", "早餐卡专享价", "第二份半价", "第二份优惠",
    "二件套", "三件套", "四件套", "五件套", "六件套", "八件套",
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


def category_rank(cat):
    """品类优先级：汉堡类最前，饮品/周边最后。"""
    c = (cat or "").replace("\n", "")
    for kw, rank in CATEGORY_RANK:
        if kw in c:
            return rank
    return 5


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


def load_rounds():
    """读官方套餐结构说明（collect_menu.py 采集自 query-meal-detail 的 rounds）。

    rounds[].name 是麦当劳官方对「这个套餐由哪几部分组成、每部分能换什么」的说明，
    比活动文案覆盖面大得多（实测 39 个套餐类商品有结构说明），且 100% 来自官方接口。
    """
    path = os.path.join(ROOT, "data", "menu_full.json")
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        menu = json.load(f)
    out = {}
    for nm, m in menu.items():
        rounds = m.get("rounds") or []
        if len(rounds) >= 2:
            out[nm] = [{"name": r.get("name"),
                        "count": r.get("count"),
                        "options": r.get("options", [])[:6]} for r in rounds]
    return out


def load_acts():
    """从 campaign-calendar 采集官方活动文案，按商品名匹配。"""
    import sys
    sys.path.insert(0, os.path.join(ROOT, "skills", "mcd-flavor-index", "scripts"))
    try:
        from mcd_client import McdClient
        cli = McdClient()
        cal = cli.call("campaign-calendar", {})
    except Exception:
        return {}
    acts = []
    for day in cal.get("dailyList", []):
        for e in day.get("events", []):
            a = e.get("articleDto", {})
            if a.get("content"):
                acts.append((day.get("date", ""), a.get("title", ""), a["content"]))
    return acts


def match_act_desc(name, acts):
    """在活动文案里找提到该商品的那句，作为官方介绍。"""
    for date, title, content in acts:
        if name not in content:
            continue
        for seg in re.split(r"[。！!\n]", content):
            seg = seg.strip()
            if name in seg and 10 < len(seg) < 100:
                return {"text": seg, "date": date, "title": title}
    return None


def main():
    ugc = load("data_ugc.json")
    menu = load("data/menu_full.json")
    rounds = load_rounds()
    acts = load_acts()

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
            "image": m.get("image") or "",
            "official_desc": (m.get("official_desc") or {}).get("text"),
            "official_rounds": rounds.get(it["name"], []),
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
        if not d.get("text"):
            d = match_act_desc(nm, acts) or {}
        item = {
            "name": nm,
            "cat": (m.get("cats") or ["在售"])[0].replace("\n", ""),
            "price": m.get("price"),
            "signal": sig,
            "flavor_tags": fl,
            "ingredients": ings,
            "image": m.get("image") or "",
            "official_desc": d.get("text"),
            "official_rounds": rounds.get(nm, []),
            "official_desc_date": d.get("date"),
            "has_review": bool(t),
            "avg": round(sum(u["score"] for u in t["ugc"]) / len(t["ugc"]), 1) if t else None,
            "n": len(t["ugc"]) if t else 0,
            "min": min((u["score"] for u in t["ugc"]), default=None) if t else None,
            "max": max((u["score"] for u in t["ugc"]), default=None) if t else None,
            "spread": (max(u["score"] for u in t["ugc"]) - min(u["score"] for u in t["ugc"])) if t else 0,
        }
        hot.append(item)
    # 排序：先按品类（用户真正常点的排前面），再按信号分、评价分、价格
    for x in hot:
        x["cat_rank"] = category_rank(x["cat"])
    hot.sort(key=lambda x: (x["cat_rank"], -x["signal"],
                            -x["avg"] if x["avg"] else 0, x["price"] or 0))

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
    print(f"  有官方套餐结构: {sum(1 for x in hot if x['official_rounds'])}")
    print(f"  有官方介绍(描述或结构): {sum(1 for x in hot if x['official_desc'] or x['official_rounds'])}")
    print(f"  带销量信号标签: {sum(1 for x in hot if x['signal'])}")
    print(f"\n→ {path}")


if __name__ == "__main__":
    main()
