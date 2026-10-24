#!/usr/bin/env python3
"""麦门真香榜 · 真香指数计算与页面生成。

用法:
  python flavor_index.py --list                     # 离线真香榜（读 data_ugc.json）
  python flavor_index.py --item 龙焰芝士棒鸡腿堡      # 单品深挖
  python flavor_index.py --sync --city 上海 --keyword 人民广场   # 拉官方标签+核价
  python flavor_index.py --render --out out.html     # 生成交互式页面

环境变量:
  MCD_MCP_TOKEN  麦当劳 MCP Token（--sync / --render 需要）
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
DATA_FILE = os.path.join(ROOT, "data_ugc.json")

# 判定"官方标签被真实口碑否定"的关键词规则。
# 只用于把评价原文里的关键表述与官方标签做对照，规则本身公开在页面上。
CONFLICT_PATTERNS = [
    ("没拉丝", "拉丝"), ("没有拉丝", "拉丝"), ("空心", "拉丝"),
    ("中空", "拉丝"), ("诈骗", "拉丝"), ("照骗", "拉丝"),
    ("缩水", ""), ("略显平淡", ""), ("中规中矩", ""),
    ("缺乏惊艳感", ""), ("趁热", ""),
]


def load_data(path=None):
    path = path or DATA_FILE
    if not os.path.exists(path):
        raise SystemExit(f"找不到数据文件：{path}")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def enrich(items):
    """补上派生字段：均值、极值、离散度、评分分布。"""
    out = []
    for it in items:
        scores = [u["score"] for u in it["ugc"]]
        n = len(scores)
        avg = sum(scores) / n if n else 0.0
        dist = {}
        for s in scores:
            dist[str(s)] = dist.get(str(s), 0) + 1
        out.append({
            **it,
            "n": n,
            "avg": round(avg, 2),
            "min": min(scores) if scores else None,
            "max": max(scores) if scores else None,
            "spread": (max(scores) - min(scores)) if scores else 0,
            "distribution": dist,
            "negative": sum(1 for s in scores if s <= 3),
        })
    return out


def detect_conflicts(item):
    """找出真实评价中与官方标签冲突的表述。

    返回 [(冲突词, 命中的评价原文, 来源)]，供页面对账区使用。
    """
    hits = []
    seen = set()
    for u in item["ugc"]:
        for kw, _ in CONFLICT_PATTERNS:
            if kw in u["text"] and kw not in seen:
                seen.add(kw)
                hits.append({"keyword": kw, "quote": u["text"], "source": u["source"]})
    return hits


def cmd_list(args):
    data = load_data(args.data)
    items = enrich(data["items"])
    items.sort(key=lambda d: -d["avg"])
    print(f"麦门真香榜 · 真香指数排行")
    print(f"样本 {sum(d['n'] for d in items)} 篇 / {len(items)} 个商品"
          f" · 采集 {data.get('collected_at','?')}\n")
    print(f"{'商品':<16}{'真香':>6}{'区间':>10}{'n':>4}{'核价':>9}  官方标签")
    print("-" * 92)
    for d in items:
        rng = f"{d['min']:.1f}-{d['max']:.1f}"
        tags = "/".join(d.get("official_tags", [])) or "-"
        print(f"{d['name']:<16}{d['avg']:>6.1f}{rng:>10}{d['n']:>4}"
              f"{('¥'+str(d.get('official_price_yuan','-'))):>9}  {tags}")
    top = max(items, key=lambda d: d["spread"])
    print(f"\n分歧最大：{top['name']}（离散度 {top['spread']:.1f}，区间 {top['min']:.1f}-{top['max']:.1f}）")
    return items


def cmd_item(args):
    data = load_data(args.data)
    items = enrich(data["items"])
    target = None
    for d in items:
        if args.item in d["name"]:
            target = d
            break
    if not target:
        print(f"没找到「{args.item}」。可选：")
        for d in items:
            print("  -", d["name"])
        return None
    print(f"【{target['name']}】真香指数 {target['avg']:.1f} / 5")
    print(f"样本 {target['n']} 篇 · 区间 {target['min']:.1f}-{target['max']:.1f}"
          f" · 离散度 {target['spread']:.1f} · 官方核价 ¥{target.get('official_price_yuan','-')}")
    print(f"\n官方风味标签：")
    for t in target.get("official_tags", []):
        print("  ·", t)
    conflicts = detect_conflicts(target)
    if conflicts:
        print(f"\n⚠ 官方标签与真实口碑的落差（{len(conflicts)} 处）：")
        for c in conflicts:
            print(f"  · 「{c['keyword']}」— {c['source']}")
            print(f"    {c['quote'][:70]}…")
    print(f"\n全部评价原文（{target['n']} 篇）：")
    for i, u in enumerate(target["ugc"], 1):
        print(f"  [{i:02d}] {u['score']}.0 ★  {u['source']}")
        print(f"      {u['text']}")
    return target


def cmd_sync(args):
    """拉取当前门店的官方标签与核价，输出对账数据。"""
    sys.path.insert(0, HERE)
    from mcd_client import McdClient, McdError
    from menu_solver import MenuSnapshot, find_store

    cli = McdClient()
    stores = find_store(cli, args.city, args.keyword)
    if not stores:
        print("没找到门店")
        return None
    store = stores[0]
    print(f"选定门店：{store['storeName']}（{store['storeCode']}）")

    snap = MenuSnapshot(cli, store["storeCode"])
    snap.load_menu()
    snap.load_details()
    snap.load_prices()
    print(f"在售商品 {len(snap.products)} 个，已核价 "
          f"{sum(1 for p in snap.products.values() if p.get('price') is not None)} 个")

    data = load_data(args.data)
    names = {d["name"] for d in data["items"]}
    sync = []
    for p in snap.products.values():
        if not p.get("name") or p["name"] not in names:
            continue
        tags = [t for t in p.get("tags", []) if t not in ("人气", "单品", "套餐", "小食")]
        sync.append({
            "name": p["name"], "code": p["code"],
            "official_tags": tags,
            "official_price_yuan": round(p["price"] / 100, 2) if p.get("price") else None,
            "categories": p.get("categories", []),
        })
        print(f"  {p['name']:<16} ¥{p['price']/100 if p.get('price') else '-':<7} {tags}")

    out = {"store": {"name": store["storeName"], "code": store["storeCode"]},
           "synced_at": args.stamp, "items": sync}
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        print(f"\n已写入 {args.out}")
    return out


def cmd_render(args):
    """生成单文件交互式真香榜 HTML。

    产物把 data/home.json 内联为 window.__FLAVOR_HOME__，
    页面在 file:// 下 fetch 失败时回退到它，保证双击即开。
    """
    home_path = os.path.join(ROOT, "data", "home.json")
    if not os.path.exists(home_path):
        raise SystemExit(f"找不到 {home_path}，先运行 scripts/build_home_data.py")
    with open(home_path, encoding="utf-8") as f:
        home = json.load(f)

    tpl_path = os.path.join(ROOT, "templates", "index.template.html")
    if not os.path.exists(tpl_path):
        raise SystemExit(f"找不到模板 {tpl_path}")
    with open(tpl_path, encoding="utf-8") as f:
        tpl = f.read()

    payload = json.dumps(home, ensure_ascii=False, indent=2)
    inject = "<script>window.__FLAVOR_HOME__ = " + payload + ";</script>"
    marker = "<script>\n/* ================= 数据 ================="
    if marker not in tpl:
        raise SystemExit("模板结构变化：找不到注入点")
    tpl = tpl.replace(marker, inject + "\n<script>\n/* ================= 数据 =================", 1)

    out = args.out or os.path.join(ROOT, "index.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(tpl)
    n_truth = len(home.get("truth", []))
    n_hot = len(home.get("hot", []))
    print(f"已生成 {out}（真香榜 {n_truth} 个 · 人气榜 {n_hot} 个）")
    return out


def main():
    ap = argparse.ArgumentParser(description="麦门真香榜 · 真香指数计算")
    ap.add_argument("--list", action="store_true", help="输出真香指数排行")
    ap.add_argument("--item", help="单品深挖")
    ap.add_argument("--sync", action="store_true", help="拉取官方标签与核价")
    ap.add_argument("--render", action="store_true", help="生成交互式 HTML")
    ap.add_argument("--city", default="上海")
    ap.add_argument("--keyword", default="人民广场")
    ap.add_argument("--data", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--stamp", default="2026-10-25")
    args = ap.parse_args()
    if args.list or not (args.item or args.sync or args.render):
        cmd_list(args)
    if args.item:
        cmd_item(args)
    if args.sync:
        cmd_sync(args)
    if args.render:
        cmd_render(args)


if __name__ == "__main__":
    main()
