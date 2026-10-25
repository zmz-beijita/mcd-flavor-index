#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从菜单数据推导「商品名 → 本地图片路径」映射。

为什么要脚本化：
  img_map.json 之前是手工维护的，改一次就散一次。改成从 menu_full.json
  的官方 image URL 推导，菜单每日轮换后重跑一次即可，映射永远不会失配。

推导规则：
  1. 商品名与菜单商品名完全一致 → 直接用该商品的官方图
  2. 显式别名表（ALIASES）→ UGC 名与菜单名对不上时的已知对应关系
  3. 规范化后匹配（去括号、去套餐后缀）→ 兜底
  4. 官方 image 为空 → 不给本地图，页面走分类占位图

用法：python scripts/build_img_map.py
"""
import json
import os
import re
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSET_DIR = os.path.join(ROOT, "assets", "mcd-brand")

# 已知别名：UGC 里的商品名与菜单官方名不完全一致的情况。
# 每一条都必须人工核过「确实是同一个商品」，否则会张冠李戴。
# 麦辣鸡腿堡 ≡ 麦辣鸡腿汉堡（菜单侧多一个「汉」字）
# 安格斯厚牛堡 ≡ 培根安格斯厚牛堡（菜单侧带「培根」前缀，同一张图）
ALIASES = {
    "麦辣鸡腿堡": "麦辣鸡腿汉堡",
    "安格斯厚牛堡": "培根安格斯厚牛堡",
    "麦香鸡汉堡": "麦香鸡",
}

# 名称规范化：去掉括号内容、套餐/单点后缀、数量前缀
DROP_PAT = re.compile(r"[（(].*?[)）]")
SUFFIXES = ["三件套", "四件套", "五件套", "六件套", "八件套", "二件套",
            "随心选", "随心配", "单点", "套餐", "精选"]


def norm(name):
    """把商品名压成可比对的短键。"""
    s = DROP_PAT.sub("", name)
    s = s.replace("\n", "").replace("\r", "").strip()
    for suf in SUFFIXES:
        if s.endswith(suf) and len(s) > len(suf):
            s = s[: -len(suf)]
    return s


def local_name(image_url):
    """官方 CDN URL → 本地文件名。"""
    if not image_url:
        return ""
    base = os.path.basename(urllib.parse.urlparse(image_url).path)
    if not base:
        return ""
    stem, ext = os.path.splitext(base)
    if ext.lower() == ".gif":
        return ""          # 本地不存 gif
    return "cdn-" + stem + ".png"


def main():
    with open(os.path.join(ROOT, "data", "menu_full.json"), encoding="utf-8") as f:
        menu = json.load(f)

    # 第一轮：完全匹配
    mapping = {}
    for name, m in menu.items():
        ln = local_name(m.get("image", ""))
        if ln:
            mapping[name] = "assets/mcd-brand/" + ln

    # 第二轮：规范化匹配（名称有后缀差异时）
    by_norm = {}
    for name, m in menu.items():
        ln = local_name(m.get("image", ""))
        if not ln:
            continue
        by_norm.setdefault(norm(name), []).append((name, ln))

    # 补齐 UGC 商品名（真香榜 9 个）的别名。
    # 优先用显式别名表（人工核过，绝不会张冠李戴），
    # 再退回规范化匹配（去括号、去套餐后缀后比较）。
    with open(os.path.join(ROOT, "data_ugc.json"), encoding="utf-8") as f:
        ugc = json.load(f)
    for it in ugc.get("items", []):
        nm = it["name"]
        if nm in mapping:
            continue

        # 显式别名
        target = ALIASES.get(nm)
        if target and target in mapping:
            mapping[nm] = mapping[target]
            continue

        u = norm(nm)
        if not u:
            continue

        # 规范化匹配：只在「非套装」候选里找，单品图和套餐图不是一回事
        def is_set(name):
            return any(s in name for s in ("件套", "套餐", "随心选", "随心配"))

        singles = {k: v for k, v in by_norm.items() if not is_set(v[0][0])}

        exact = singles.get(u)
        if exact and len(exact) == 1:
            mapping[nm] = "assets/mcd-brand/" + exact[0][1]
            continue

        cands = [k for k in singles
                 if k and (k.startswith(u) or u.startswith(k)
                           or k in u or u in k)]
        if not cands:
            continue
        best = max(cands, key=len)
        lst = singles[best]
        if len(lst) == 1:
            mapping[nm] = "assets/mcd-brand/" + lst[0][1]

    # 补下载：菜单轮换后会有新品，官方图地址在 menu_full.json 里是现成的。
    # 不补的话，定时更新后新上架的商品会缺图（页面走分类占位）。
    #
    # 顺序很重要：先按「文件是否真的存在」过滤，再对缺图的商品去下载。
    # 反过来做会死循环——第一轮 mapping 里已经有新品，但文件还没下，
    # 于是被误判为「已处理」而跳过下载。
    mapping = {k: v for k, v in mapping.items()
               if os.path.exists(os.path.join(ROOT, v))}

    downloaded = 0
    for name, m in menu.items():
        if name in mapping:
            continue
        ln = local_name(m.get("image", ""))
        if not ln:
            continue
        url = m["image"]
        dst = os.path.join(ASSET_DIR, ln)
        if os.path.exists(dst):
            # 文件已在本地图里，只是上一轮映射没建立（如别名商品）
            mapping[name] = "assets/mcd-brand/" + ln
            continue
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "wb"})
            with urllib.request.urlopen(req, timeout=30) as r:
                data = r.read()
            if len(data) < 500:          # 明显不是图片（多半是错误页）
                continue
            with open(dst, "wb") as f:
                f.write(data)
            mapping[name] = "assets/mcd-brand/" + ln
            downloaded += 1
        except Exception as e:
            print(f"  ! 下载失败 {name}: {str(e)[:60]}", flush=True)

    out = os.path.join(ROOT, "data", "img_map.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=1, sort_keys=True)

    print(f"映射 {len(mapping)} 条（菜单 {len(menu)} 个商品）")
    if downloaded:
        print(f"新下载商品图 {downloaded} 张")
    missing = [k for k in menu if k not in mapping]
    print(f"无本地图 {len(missing)} 个")
    if missing:
        print("  例：" + "、".join(missing[:8]))
    print(f"→ {out}")


if __name__ == "__main__":
    main()
