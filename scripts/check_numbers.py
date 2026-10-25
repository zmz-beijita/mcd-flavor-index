#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数字一致性自检：页面与生成脚本必须算出同一组数字。

背景：社交预览图脚本曾把「评分离散度≥3 的商品数」（1 个）当成
「官方标签落差」（3 个）——两个同名不同义的指标混用，
预览图和页面显示的数字对不上。这类问题肉眼极难发现，必须脚本化守住。

检查项：
  1. 页面模板的 DENY 规则 与 预览图脚本的 DENY 规则 语义一致
  2. 落差数：页面算法 == 预览图脚本算法
  3. 评价篇数 / 在售商品数：data_ugc.json == data/home.json == 小程序 flavor.json
  4. index.html 内联数据 == data/home.json（且统计数字渲染正确）
  5. README 里写的关键数字与实际一致

用法：python scripts/check_numbers.py
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAIL = []
OK = []


def check(name, cond, detail=""):
    (OK if cond else FAIL).append(f"{name}{(' — ' + detail) if detail else ''}")
    print(f"  {'✅' if cond else '❌'} {name}{(' — ' + detail) if detail else ''}")


def load(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return json.load(f)


# ---------- 页面模板的 DENY 规则 ----------
def page_deny(tpl):
    m = re.search(r"const DENY=\[(.*?)\];", tpl, re.S)
    rules = []
    for mm in re.finditer(
            r"\{re:/(.*?)/,neg:/(.*?)/\}", m.group(1)):
        rules.append((mm.group(1), mm.group(2).split("|")))
    return rules


def preview_deny(script):
    m = re.search(r"DENY = \[(.*?)\n    \]", script, re.S)
    rules = []
    for mm in re.finditer(r're\.compile\("(.*?)"\),\s*\((.*?)\)\)', m.group(1)):
        negs = re.findall(r'"([^"]+)"', mm.group(2))
        rules.append((mm.group(1), negs))
    return rules


def count_gaps(truth, rules):
    n = 0
    for x in truth:
        for tag in x.get("official_tags", []):
            hit = False
            for pat, negs in rules:
                if re.search(pat, tag) and any(
                        neg in r for r in (x.get("real") or []) for neg in negs):
                    hit = True
                    break
            if hit:
                n += 1
                break
    return n


def main():
    print("\n=== 1. 落差判定规则一致性 ===")
    tpl = open(os.path.join(ROOT, "templates", "index.template.html"),
               encoding="utf-8").read()
    prev = open(os.path.join(ROOT, "scripts", "build_social_preview.py"),
                encoding="utf-8").read()
    rp, rv = page_deny(tpl), preview_deny(prev)
    check("规则条数一致", len(rp) == len(rv), f"页面 {len(rp)} 条 / 脚本 {len(rv)} 条")
    same = len(rp) == len(rv) and all(
        rp[i][0] == rv[i][0] and set(rp[i][1]) == set(rv[i][1])
        for i in range(len(rp)))
    check("规则内容一致", same,
          "" if same else f"页面 {rp} vs 脚本 {rv}")

    home = load("data/home.json")
    ugc = load("data_ugc.json")
    mp = load(os.path.join("miniprogram", "data", "flavor.json"))

    print("\n=== 2. 落差数字一致 ===")
    gap_page = count_gaps(home["truth"], rp)
    gap_prev = count_gaps(home["truth"], rv)
    check("两种算法结果一致", gap_page == gap_prev, f"{gap_page} vs {gap_prev}")
    check("落差数 > 0", gap_page > 0, f"{gap_page} 处")

    print("\n=== 3. 评价篇数 / 在售数一致 ===")
    n_ugc = sum(len(i.get("ugc", [])) for i in ugc["items"])
    n_home = sum(len(t["ugc"]) for t in home["truth"])
    n_mp = sum(len(i["ugc"]) for i in mp["items"])
    check("data_ugc / home.json / 小程序 评价篇数一致",
          n_ugc == n_home == n_mp, f"{n_ugc} / {n_home} / {n_mp}")
    check("在售商品数一致",
          len(home["hot"]) == len(mp["hot"]), f"{len(home['hot'])} / {len(mp['hot'])}")
    check("真香榜商品数一致",
          len(home["truth"]) == len(mp["items"]), f"{len(home['truth'])} / {len(mp['items'])}")

    print("\n=== 4. index.html 内联数据与渲染 ===")
    html = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
    i = html.index("window.__FLAVOR_HOME__ = ")
    j = html.index(";</script>", i)
    inline = json.loads(html[i + len("window.__FLAVOR_HOME__ = "):j])
    check("内联 truth 与 home.json 一致",
          [x["name"] for x in inline["truth"]] == [x["name"] for x in home["truth"]])
    check("内联 hot 数量一致", len(inline["hot"]) == len(home["hot"]))
    img_i = html.index("window.__FLAVOR_IMG__ = ")
    img_j = html.index(";</script>", img_i)
    check("内联图片映射与 img_map.json 一致",
          json.loads(html[img_i + len("window.__FLAVOR_IMG__ = "):img_j])
          == load("data/img_map.json"))

    print("\n=== 5. README 关键数字 ===")
    rm = open(os.path.join(ROOT, "README.md"), encoding="utf-8").read()
    check("README 评价篇数", f"{n_ugc} 篇真实评价" in rm, f"应为 {n_ugc} 篇")
    check("README 在售数", f"{len(home['hot'])} 个当前在售" in rm,
          f"应为 {len(home['hot'])} 个")
    bad = re.findall(r"\b(\d{2,3}) 篇(真实|公开)评价", rm)
    stale = [b for b in bad if b[0] != str(n_ugc)]
    check("README 无过期篇数", not stale, f"发现 {stale}" if stale else "")

    print("\n" + "=" * 52)
    if FAIL:
        print(f"❌ {len(FAIL)} 项不通过：")
        for f in FAIL:
            print("   -", f)
        sys.exit(1)
    print(f"✅ 全部 {len(OK)} 项通过")


if __name__ == "__main__":
    main()
