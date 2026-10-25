#!/usr/bin/env python3
"""通过 GitHub REST API 把本地目录推送到仓库（绕过 git 协议，适配代理环境）。

用法: python push_via_api.py <repo_slug> <local_dir>
"""
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request

TOKEN = os.environ.get("GITHUB_TOKEN", "")
API = "https://api.github.com"


def api(method, path, data=None):
    """发一个 GitHub API 请求；失败抛 RuntimeError（不 SystemExit，便于重试）。"""
    url = API + path
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Authorization", f"Bearer {TOKEN}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    req.add_header("User-Agent", "mcd-flavor-push")
    if body:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:400]
        raise RuntimeError(f"HTTP {e.code}: {detail}")
    except Exception as e:
        raise RuntimeError(str(e))


def get_sha(repo, path):
    """取文件当前 sha；文件不存在或仓库为空时返回 None（正常首次上传）。"""
    url = API + f"/repos/{repo}/contents/{path}"
    req = urllib.request.Request(url, method="GET")
    req.add_header("Authorization", f"Bearer {TOKEN}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "mcd-flavor-push")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read().decode() or "{}")
            return data.get("sha") if isinstance(data, dict) else None
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise RuntimeError(f"HTTP {e.code}: {e.read().decode('utf-8','replace')[:300]}")
    except Exception as e:
        raise RuntimeError(str(e))


def main():
    if not TOKEN:
        raise SystemExit("需要设置 GITHUB_TOKEN 环境变量")
    repo = sys.argv[1]
    root = sys.argv[2]
    files = []
    # 凭据文件绝不能进仓库
    SKIP_FILES = {".env", ".env.local", ".env.production"}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames
                       if d not in (".git", "__pycache__", ".venv", "node_modules")]
        for fn in filenames:
            if fn.endswith((".pyc", ".pyo")):
                continue
            if fn in SKIP_FILES:
                print(f"  ! 跳过凭据文件 {fn}", flush=True)
                continue
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, root).replace("\\", "/")
            files.append((rel, full))
    files.sort()

    import concurrent.futures as cf

    def upload(item):
        rel, full = item
        with open(full, "rb") as f:
            content = base64.b64encode(f.read()).decode()
        last = None
        for attempt in range(10):
            try:
                sha = get_sha(repo, rel)
            except BaseException as e:
                last = str(e)
                if attempt < 9:
                    time.sleep(min(1.5 * (attempt + 1), 12))
                    continue
                raise RuntimeError(last)
            payload = {
                "message": f"feat: {rel}" if not sha else f"chore: update {rel}",
                "content": content,
                "branch": "master",
            }
            if sha:
                payload["sha"] = sha
            try:
                api("PUT", f"/repos/{repo}/contents/{rel}", payload)
                return rel
            except BaseException as e:      # SystemExit 也是 BaseException
                last = str(e)
                if attempt < 9:
                    time.sleep(min(1.5 * (attempt + 1), 12))
                    continue
                raise RuntimeError(last)
        raise RuntimeError(last or "unknown")

    ok = 0
    errors = []
    # 代理环境下 502/409 较多，低并发 + 指数退避比高并发更快收敛
    with cf.ThreadPoolExecutor(max_workers=3) as ex:
        futs = {ex.submit(upload, it): it for it in files}
        for fut in cf.as_completed(futs):
            rel = futs[fut][0]
            try:
                fut.result()
                ok += 1
                print(f"  ✓ {rel}", flush=True)
            except Exception as e:
                errors.append((rel, str(e)[:120]))
                print(f"  ✗ {rel}: {str(e)[:120]}", flush=True)
    print(f"\n已上传 {ok}/{len(files)} 个文件到 {repo}（分支 master）")
    if errors:
        print("失败：")
        for rel, e in errors:
            print(f"  - {rel}: {e}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
