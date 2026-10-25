#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一键更新：拉官方数据 → 重建 → 渲染 → 校验 → 推送。

麦当劳菜单每日轮换（凌晨切早餐、上午切正餐），商品、价格、官方标签都会变。
这个脚本把整条链路串成一条命令，供定时任务调用。

用法：
    python scripts/refresh_all.py            # 只更新本地，不推送
    python scripts/refresh_all.py --push     # 更新并推送到 GitHub
    python scripts/refresh_all.py --dry-run  # 只跑一遍链路看结果

需要环境变量：
    MCD_MCP_TOKEN   麦当劳 MCP Token
    GITHUB_TOKEN    GitHub PAT（仅 --push 需要）

数据来源分层（重要）：
  - 官方侧（菜单/标签/核价/配料/套餐结构/图片）→ 本脚本全自动刷新
  - 真实评价（data_ugc.json）→ 需要人工/Agent 用 WebSearch 采集后手工替换，
    本脚本**不会**覆盖它，以免把精心采集的来源标注冲掉
"""
import argparse
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable
STORE = "1450713"


def run(desc, cmd, cwd=ROOT, check=True):
    print(f"\n>>> {desc}")
    print(f"    $ {' '.join(cmd)}", flush=True)
    t0 = time.time()
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    out = (r.stdout or "") + (r.stderr or "")
    tail = [l for l in out.strip().split("\n") if l.strip()][-6:]
    for l in tail:
        print("    " + l)
    print(f"    ({time.time() - t0:.1f}s, exit={r.returncode})")
    if check and r.returncode != 0:
        raise SystemExit(f"步骤失败：{desc}")
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--push", action="store_true", help="推送到 GitHub")
    ap.add_argument("--dry-run", action="store_true", help="只跑链路不推送")
    ap.add_argument("--store", default=STORE)
    args = ap.parse_args()

    if not os.environ.get("MCD_MCP_TOKEN"):
        print("⚠️ 未设置 MCD_MCP_TOKEN，将无法拉取官方数据")

    print("=" * 62)
    print("麦门真香榜 · 全量更新")
    print("=" * 62)

    # 1) 拉官方数据（菜单每日轮换，必须实时拉）
    run("采集门店菜单（标签/配料/套餐结构/核价）",
        [PY, "scripts/collect_menu.py", "--store", args.store])

    # 2) 重建首页数据（真香榜 + 人气榜）
    run("生成首页双榜数据", [PY, "scripts/build_home_data.py"])

    # 3) 重建图片映射（自动补下载新品官方图）
    run("推导商品→图片映射（含自动补下载）", [PY, "scripts/build_img_map.py"])

    # 4) 渲染单文件页面
    run("渲染 index.html",
        [PY, "skills/mcd-flavor-index/scripts/flavor_index.py", "--render"])

    # 5) 同步小程序
    run("同步微信小程序数据", [PY, "scripts/sync_miniprogram.py"])

    # 6) 重生成社交图
    run("重生成 GitHub 社交预览图", [PY, "scripts/build_social_preview.py"])
    run("重生成社媒引流长图", [PY, "scripts/build_social_card.py"])

    # 7) 数字一致性自检（防止各处数字漂移）
    #    --fix：README 里的「N 个在售」随菜单轮换变化，自动改写
    run("数字一致性自检（并同步 README 数字）",
        [PY, "scripts/check_numbers.py", "--fix"])

    # 8) 推送
    if args.push and not args.dry_run:
        if not os.environ.get("GITHUB_TOKEN"):
            raise SystemExit("需要 GITHUB_TOKEN")
        run("推送到 GitHub",
            [PY, "examples/push_via_api.py", "zmz-beijita/mcd-flavor-index", "."])
    elif args.push:
        print("\n(dry-run：跳过推送)")
    else:
        print("\n(未指定 --push，仅更新本地)")

    print("\n" + "=" * 62)
    print("✅ 更新完成")
    print("   线上地址：https://zmz-beijita.github.io/mcd-flavor-index/")
    print("   GitHub Pages 有 1-3 分钟构建延迟，稍后自动生效")
    print("=" * 62)


if __name__ == "__main__":
    main()
