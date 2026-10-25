#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一次性生成 README / 社交预览需要的全部页面截图。

之前截图是手工零散截的，结果留下三个问题：
  1. `docs/screenshots/` 整个目录是 `docs/` 的旧副本（社交预览图还是「34 篇」那版）
  2. `screenshot-full.png` / `screenshot-hot.png` 是旧数据（118 个在售）
  3. `screenshot-comments.png` 与 `screenshot-plaza.png` 内容完全重复

这个脚本统一生成，产物与当前数据一致，可挂进定时刷新流程。

用法：python scripts/build_screenshots.py
"""
import base64
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs")
CHROME = os.path.expanduser(
    "~/AppData/Local/ms-playwright/chromium-1234/chrome-win64/chrome.exe")


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


class CDP:
    def __init__(self, url, width=1440, height=900):
        self.port = free_port()
        self.prof = tempfile.mkdtemp()
        self.proc = subprocess.Popen(
            [CHROME, "--headless=new", f"--remote-debugging-port={self.port}",
             f"--user-data-dir={self.prof}", "--no-first-run", "--disable-gpu",
             "--hide-scrollbars", f"--window-size={width},{height}", url],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        ws = None
        for _ in range(80):
            try:
                d = json.load(urllib.request.urlopen(
                    f"http://127.0.0.1:{self.port}/json", timeout=1))
                pg = [x for x in d if x.get("type") == "page"
                      and x.get("webSocketDebuggerUrl")]
                if pg:
                    ws = pg[0]["webSocketDebuggerUrl"]
                    break
            except Exception:
                time.sleep(0.2)
        if not ws:
            raise SystemExit("无法连接 DevTools")
        host, path = ws.replace("ws://", "").split("/", 1)
        self.host, self.port2 = host.split(":")
        self.path = path
        key = base64.b64encode(os.urandom(16)).decode()
        self.sock = socket.create_connection((self.host, int(self.port2)))
        self.sock.sendall(
            (f"GET /{self.path} HTTP/1.1\r\nHost: {self.host}:{self.port2}\r\n"
             f"Upgrade: websocket\r\nConnection: Upgrade\r\n"
             f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n").encode())
        self.buf = b""
        while b"\r\n\r\n" not in self.buf:
            self.buf += self.sock.recv(4096)
        self.buf = b""
        self.mid = 0

    def _send(self, method, params):
        self.mid += 1
        mid = self.mid
        payload = json.dumps({"id": mid, "method": method, "params": params}).encode()
        n = len(payload)
        if n < 126:
            head = bytes([0x81, 0x80 | n])
        elif n < 65536:
            head = bytes([0x81, 0xFE]) + n.to_bytes(2, "big")
        else:
            head = bytes([0x81, 0xFF]) + n.to_bytes(8, "big")
        mask = os.urandom(4)
        masked = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
        self.sock.sendall(head + mask + masked)
        while True:
            while len(self.buf) < 2:
                self.buf += self.sock.recv(65536)
            b0, b1 = self.buf[0], self.buf[1]
            ln = b1 & 0x7F
            off = 2
            if ln == 126:
                while len(self.buf) < 4:
                    self.buf += self.sock.recv(65536)
                ln = int.from_bytes(self.buf[2:4], "big")
                off = 4
            elif ln == 127:
                while len(self.buf) < 10:
                    self.buf += self.sock.recv(65536)
                ln = int.from_bytes(self.buf[2:10], "big")
                off = 10
            while len(self.buf) < off + ln:
                self.buf += self.sock.recv(65536)
            data = self.buf[off:off + ln]
            self.buf = self.buf[off + ln:]
            if b0 & 0x0F == 1:
                m = json.loads(data)
                if m.get("id") == mid:
                    return m

    def evaluate(self, expr):
        r = self._send("Runtime.evaluate",
                       {"expression": expr, "returnByValue": True,
                        "awaitPromise": True})
        return r.get("result", {}).get("result", {}).get("value")

    def shot(self, out, x, y, w, h):
        r = self._send("Page.captureScreenshot",
                       {"format": "png", "captureBeyondViewport": True,
                        "clip": {"x": x, "y": y, "width": w, "height": h, "scale": 1}})
        data = r.get("result", {}).get("data")
        if not data:
            raise SystemExit("截图失败：" + out)
        with open(out, "wb") as f:
            f.write(base64.b64decode(data))
        print(f"  ✓ {os.path.relpath(out, ROOT)}  ({int(w)}x{int(h)})")

    def close(self):
        try:
            self.sock.close()
        except Exception:
            pass
        self.proc.terminate()
        time.sleep(0.2)
        shutil.rmtree(self.prof, ignore_errors=True)


def box_of(cdp, js_expr):
    """取元素的边界框（含 24px 留白）。"""
    r = cdp.evaluate(
        f'(()=>{{const e={js_expr}; if(!e) return null;'
        f'const r=e.getBoundingClientRect();'
        f'return JSON.stringify({{x:Math.max(0,r.left-24),'
        f'y:Math.max(0,r.top+window.scrollY-24),'
        f'w:Math.min(1440,r.width+48), h:e.offsetHeight+48}})}})()')
    return json.loads(r) if r else None


def main():
    os.makedirs(DOCS, exist_ok=True)
    html = os.path.join(ROOT, "index.html")
    url = "file://" + os.path.abspath(html)
    cdp = CDP(url, 1440, 1000)
    try:
        time.sleep(3)
        cdp.evaluate("(async()=>{try{await document.fonts.ready;}catch(e){}return 1})()")
        time.sleep(0.8)

        jobs = [
            # (输出文件, 目标 JS 表达式, 额外动作)
            ("screenshot-hero.png", "document.querySelector('.hero')", None),
            ("screenshot-stats.png", "document.querySelector('.stats')", None),
            ("screenshot-rank.png", "document.getElementById('truthList')", None),
            ("screenshot-hot.png", "document.getElementById('hotList')", None),
            ("screenshot-plaza.png", "document.getElementById('cmt')", None),
            ("screenshot-source.png", "document.querySelector('.foot')", None),
        ]
        for name, expr, _ in jobs:
            b = box_of(cdp, expr)
            if not b:
                print(f"  ! 跳过 {name}：找不到元素")
                continue
            cdp.shot(os.path.join(DOCS, name), b["x"], b["y"], b["w"], b["h"])

        # 展开某个商品后的详情卡（真香榜第 1 名龙焰芝士棒鸡腿堡）
        cdp.evaluate("toggleItem('龙焰芝士棒鸡腿堡')")
        time.sleep(1.2)
        b = box_of(cdp, "[...document.querySelectorAll('.rank-item')]"
                        ".find(r=>r.dataset.name==='龙焰芝士棒鸡腿堡')")
        if b:
            cdp.shot(os.path.join(DOCS, "screenshot-detail.png"),
                     b["x"], b["y"], b["w"], b["h"])

        # 整页长图
        h = cdp.evaluate("document.body.scrollHeight")
        cdp.shot(os.path.join(DOCS, "screenshot-full.png"), 0, 0, 1440, h)

    finally:
        cdp.close()

    # 清理冗余：docs/screenshots/ 是 docs/ 的旧副本，且 comments/plaza 重复
    dup = os.path.join(DOCS, "screenshots")
    if os.path.isdir(dup):
        shutil.rmtree(dup)
        print("  ✓ 已删除冗余目录 docs/screenshots/（docs/ 的旧副本）")
    for junk in ("_plaza.png", "screenshot-comments.png",
                 "screenshot-comments-negative.png"):
        p = os.path.join(DOCS, junk)
        if os.path.exists(p):
            os.remove(p)
            print(f"  ✓ 已删除冗余文件 docs/{junk}")

    # 广场完整图有 6000+ px 高，放 README 里太长。
    # 额外裁一份「顶部版」：发帖框 + 前两个分组，够看清功能。
    plaza = os.path.join(DOCS, "screenshot-plaza.png")
    top = os.path.join(DOCS, "screenshot-plaza-top.png")
    if os.path.exists(plaza):
        try:
            from PIL import Image
            im = Image.open(plaza)
            im.crop((0, 0, im.width, min(1500, im.height))).save(top)
            print(f"  ✓ docs\\screenshot-plaza-top.png  ({im.width}x{min(1500, im.height)})")
        except Exception as e:
            print(f"  ! 广场顶部版裁剪失败：{str(e)[:60]}")

    print("\n全部截图已按当前数据重新生成")


if __name__ == "__main__":
    main()
