#!/usr/bin/env python3
"""采集门店菜单全量官方信息：标签 / 配料清单 / 套餐结构说明 / 官方核价。

数据源全部为麦当劳 MCP 官方接口：
  query-meals        → 在售分类与官方风味标签（tags）
  query-meal-detail  → 配料清单（modification）与套餐结构说明（rounds）
  calculate-price   → 官方核价（单位分）

注意：菜单编码每日轮换，本脚本每次都实时拉取菜单，绝不硬编码 productCode。

用法：python scripts/collect_menu.py --store 1450713 --out data/menu_full.json
"""
import argparse
import concurrent.futures as cf
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "skills", "mcd-flavor-index", "scripts"))

from mcd_client import McdClient, McdError  # noqa: E402
from menu_solver import MenuSnapshot  # noqa: E402

# 冰量 / 甜度选项不是配料
ICE_ONLY = {"标准", "去冰", "多冰", "少冰", "不加", "加", "换燕麦奶", "奶油球", "白砂糖"}


def collect(cli, store_code, workers=5):
    snap = MenuSnapshot(cli, store_code)
    snap.load_menu()
    snap.load_details()
    snap.load_prices()

    codes = [(c, p["name"]) for c, p in snap.products.items() if p.get("name")]
    print(f"在售商品 {len(codes)} 个，开始采集详情…", flush=True)

    def fetch(item):
        code, name = item
        rounds, ings = [], []
        for _ in range(3):
            try:
                d = cli.call("query-meal-detail",
                            {"storeCode": store_code, "orderType": "1",
                             "beType": 1, "code": code})
                for r in (d.get("rounds") or []):
                    if r.get("name"):
                        rounds.append({
                            "name": r["name"],
                            "count": len(r.get("choices") or []),
                            "options": [c.get("name")
                                        for c in (r.get("choices") or [])][:8],
                        })
                for g in d.get("modification", {}).get("items", []):
                    for v in g.get("values", []):
                        n = v.get("name")
                        if n and n not in ings:
                            ings.append(n)
                break
            except McdError:
                continue
        return name, rounds, ings

    detail = {}
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        for i, (name, rounds, ings) in enumerate(ex.map(fetch, codes), 1):
            detail[name] = (rounds, ings)
            if i % 20 == 0:
                print(f"  {i}/{len(codes)}", flush=True)

    out = {}
    for code, p in snap.products.items():
        name = p.get("name")
        if not name:
            continue
        rounds, ings = detail.get(name, ([], []))
        out[name] = {
            "code": code,
            "price": round(p["price"] / 100, 2) if p.get("price") else None,
            "cats": p.get("categories", []),
            "tags": p.get("tags", []),
            "ings": [x for x in ings if x not in ICE_ONLY][:8],
            "rounds": rounds,
        }

    # 保留已有的活动文案匹配结果
    path = os.path.join(ROOT, "data", "menu_full.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            old = json.load(f)
        for nm, v in out.items():
            if nm in old and old[nm].get("official_desc"):
                v["official_desc"] = old[nm]["official_desc"]
                v["official_desc_date"] = old[nm].get("official_desc_date")

    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    n_rounds = sum(1 for v in out.values() if len(v["rounds"]) >= 2)
    n_ings = sum(1 for v in out.values() if v["ings"])
    n_tags = sum(1 for v in out.values() if v["tags"])
    print(f"\n已写入 {path}")
    print(f"  商品总数        {len(out)}")
    print(f"  有官方风味标签  {n_tags}")
    print(f"  有官方配料清单  {n_ings}")
    print(f"  有套餐结构说明  {n_rounds}")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--store", default="1450713")
    ap.add_argument("--out", default="data/menu_full.json")
    args = ap.parse_args()
    cli = McdClient()
    collect(cli, args.store)


if __name__ == "__main__":
    main()
