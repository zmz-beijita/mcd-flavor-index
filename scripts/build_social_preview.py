#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 GitHub 社交预览图（1200×630）。

数字全部从 data/home.json + data_ugc.json 读取后注入，
不会像上一版那样写着过期的「34 篇 / 96 个」。

用法：python scripts/build_social_preview.py
"""
import base64
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROME = os.path.expanduser(
    "~/AppData/Local/ms-playwright/chromium-1234/chrome-win64/chrome.exe")

TPL = """<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{width:1200px;height:630px;overflow:hidden;
  font-family:"PingFang SC","Microsoft YaHei","Noto Sans SC",sans-serif;
  background:linear-gradient(135deg,#FFF9E8 0%,#FFF3D6 42%,#FFE9C8 100%);
  color:#2B2520;position:relative}
.wrap{padding:44px 60px}
.brand{display:flex;align-items:center;gap:16px}
.logo{width:52px;height:52px;border-radius:16px;background:#E8342A;color:#fff;
  font-size:29px;font-weight:900;display:flex;align-items:center;justify-content:center;
  box-shadow:0 5px 0 #B32018}
.bname{font-size:29px;font-weight:900;letter-spacing:-1px}
.kicker{margin-top:24px;font-size:19px;font-weight:900;color:#E8342A;letter-spacing:5px}
h1{margin-top:10px;font-size:62px;font-weight:900;line-height:1.08;letter-spacing:-3px}
.vs{display:inline-flex;align-items:center;justify-content:center;
  background:#FFC72C;color:#2B2520;font-size:32px;font-weight:900;
  padding:2px 16px;border-radius:16px;box-shadow:0 6px 0 #D99A00;
  margin-right:16px;vertical-align:middle;transform:translateY(-4px)}
.sub{margin-top:20px;font-size:25px;color:#6B5F52;line-height:1.65;font-weight:700}
.sub b{color:#E8342A}
.chips{margin-top:22px;display:flex;gap:14px}
.chip{padding:11px 26px;border-radius:16px;font-size:23px;font-weight:900;
  box-shadow:0 5px 0 rgba(0,0,0,.09)}
.chip.red{background:#E8342A;color:#fff;box-shadow:0 5px 0 #B32018}
.chip.yellow{background:#FFC72C;color:#2B2520;box-shadow:0 5px 0 #D99A00}
.rule{height:3px;background:#EADCC4;margin-top:26px}
.stats{margin-top:22px;display:flex;align-items:flex-end;gap:48px}
.st .n{font-size:46px;font-weight:900;line-height:1;letter-spacing:-2px}
.st .l{margin-top:7px;font-size:18px;color:#8B7E70;font-weight:700}
.st.red .n{color:#E8342A}.st.blue .n{color:#2B8FE0}
.st.red2 .n{color:#E8342A}.st.big .n{font-size:48px;color:#2B2520}
.foot{position:absolute;right:60px;bottom:36px;font-size:18px;color:#B3A695;font-weight:700}
.deco{position:absolute;right:-90px;top:-90px;width:420px;height:420px;
  border-radius:50%;background:rgba(232,52,42,.06)}
.deco2{position:absolute;right:120px;bottom:-140px;width:320px;height:320px;
  border-radius:50%;background:rgba(255,199,44,.16)}
</style></head><body>
<div class="deco"></div><div class="deco2"></div>
<div class="wrap">
  <div class="brand"><div class="logo">香</div><div class="bname">麦门真香榜</div></div>
  <div class="kicker">MCD FLAVOR INDEX</div>
  <h1><span class="vs">VS</span>官方说的<br>大家说的</h1>
  <div class="sub">麦当劳官方风味标签 × <b>{N_UGC} 篇真实公开评价</b> 摊开对账<br>
    真香指数 · 评分离散度 · 官方标签落差 · 你也能投票写理由</div>
  <div class="chips"><div class="chip red">🏆 真香榜</div><div class="chip yellow">✍️ 麦门广场</div></div>
  <div class="rule"></div>
  <div class="stats">
    <div class="st red"><div class="n">{N_UGC}</div><div class="l">篇真实评价</div></div>
    <div class="st blue"><div class="n">{N_HOT}</div><div class="l">个在售商品</div></div>
    <div class="st red2"><div class="n">{N_GAP}</div><div class="l">处官方标签落差</div></div>
    <div class="st big"><div class="n">5★↔2★</div><div class="l">同一商品两极评价</div></div>
  </div>
</div>
<div class="foot">基于麦当劳中国 MCP · 非官方产品</div>
</body></html>"""


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


class CDP:
    def __init__(self, url, width, height):
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
                       {"expression": expr, "returnByValue": True})
        return r.get("result", {}).get("result", {}).get("value")

    def shot(self, out, w, h):
        r = self._send("Page.captureScreenshot",
                       {"format": "png", "captureBeyondViewport": True,
                        "clip": {"x": 0, "y": 0, "width": w, "height": h, "scale": 1}})
        data = r.get("result", {}).get("data")
        if not data:
            raise SystemExit("截图失败")
        with open(out, "wb") as f:
            f.write(base64.b64decode(data))

    def close(self):
        try:
            self.sock.close()
        except Exception:
            pass
        self.proc.terminate()
        time.sleep(0.2)
        shutil.rmtree(self.prof, ignore_errors=True)


def count_tag_gaps(truth):
    """统计「官方标签落差」——必须与页面模板的 DENY 规则完全一致。

    页面（templates/index.template.html）的定义是：
      官方标签命中 DENY 正则，且该商品的真实共识里出现对应的否定表述。
    判定规则公开在页面里，不做黑箱。改这里必须同步改页面。

    注意：曾误用「评分离散度≥3」当落差数——那是另一个指标
    （离散度≥3 的只有龙焰芝士棒 1 个，而落差是 3 个）。
    """
    DENY = [
        (re.compile("拉丝"), ("没拉丝", "没有拉丝", "空心", "中空")),
        (re.compile("趁热"), ("趁热",)),
        (re.compile("人气|爆款|经典"), ("缩水",)),
    ]
    n = 0
    for x in truth:
        for tag in x.get("official_tags", []):
            for pat, negs in DENY:
                if pat.search(tag) and any(
                        neg in r for r in (x.get("real") or []) for neg in negs):
                    n += 1
                    break
            else:
                continue
            break
    return n


def main():
    with open(os.path.join(ROOT, "data", "home.json"), encoding="utf-8") as f:
        home = json.load(f)
    with open(os.path.join(ROOT, "data_ugc.json"), encoding="utf-8") as f:
        ugc = json.load(f)

    n_ugc = sum(len(i.get("ugc", [])) for i in ugc.get("items", []))
    n_hot = len(home.get("hot", []))
    n_gap = count_tag_gaps(home.get("truth", []))

    html = (TPL.replace("{N_UGC}", str(n_ugc))
                .replace("{N_HOT}", str(n_hot))
                .replace("{N_GAP}", str(n_gap)))
    tmp = os.path.join(ROOT, "docs", "_social-preview.html")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(html)

    cdp = CDP("file://" + os.path.abspath(tmp), 1200, 630)
    try:
        time.sleep(2.2)
        # 等字体加载完成（否则首帧用 fallback 字体，度量不同会导致排版塌）
        cdp.evaluate("(async()=>{try{await document.fonts.ready;}catch(e){}"
                     "await new Promise(r=>requestAnimationFrame("
                     "()=>requestAnimationFrame(r)));return true;})()")
        time.sleep(1.2)
        out = os.path.join(ROOT, "docs", "social-preview.png")
        cdp.shot(out, 1200, 630)
        print(f"已生成 {out}")
        print(f"  数字来源: {n_ugc} 篇评价 / {n_hot} 个在售 / {n_gap} 处落差")
    finally:
        cdp.close()
        if os.path.exists(tmp):
            os.remove(tmp)


if __name__ == "__main__":
    main()
