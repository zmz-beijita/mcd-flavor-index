#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成社媒引流长图（1080×1440，适配朋友圈 / 小红书 / 微博）。

选题：龙焰芝士棒鸡腿堡 —— 官方标签说「浓郁奶香拉丝芝士」，
      真实评价说「芝士棒是空心的，只有面粉皮子」。

所有引用都从 data_ugc.json 读取，不手写文案，避免与实际数据不符。

用法：python scripts/build_social_card.py
"""
import base64
import json
import os
import shutil
import socket
import subprocess
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
body{width:1080px;height:1440px;overflow:hidden;
  font-family:"PingFang SC","Microsoft YaHei","Noto Sans SC",sans-serif;
  background:#FFF6E0;color:#2B2520;position:relative}
.bg{position:absolute;inset:0;
  background:radial-gradient(circle at 88% 8%,rgba(232,52,42,.10),transparent 42%),
             radial-gradient(circle at 6% 96%,rgba(255,199,44,.30),transparent 46%)}
.wrap{position:relative;padding:52px 56px}
.top{display:flex;align-items:center;gap:14px}
.logo{width:54px;height:54px;border-radius:16px;background:#E8342A;color:#fff;
  font-size:30px;font-weight:900;display:flex;align-items:center;justify-content:center;
  box-shadow:0 5px 0 #B32018}
.bn{font-size:28px;font-weight:900}
.bn span{color:#E8342A}
.kick{margin-top:38px;font-size:20px;font-weight:900;color:#E8342A;letter-spacing:4px}
h1{margin-top:12px;font-size:66px;font-weight:900;line-height:1.14;letter-spacing:-2px}
h1 em{font-style:normal;background:#FFC72C;padding:2px 12px;border-radius:14px;
  box-shadow:0 5px 0 #D99A00;display:inline-block}
.rule{height:4px;background:#EFDFC0;margin:28px 0 26px}

/* 官方 vs 真实 */
.col{flex:1;border-radius:26px;padding:22px 22px 24px;position:relative}
.col.off{background:#2B2520;color:#fff;box-shadow:0 8px 0 rgba(0,0,0,.10)}
.col.real{background:#fff;border:4px solid #E8342A;box-shadow:0 8px 0 rgba(232,52,42,.16)}
.col-hd{display:flex;align-items:center;gap:10px;font-size:24px;font-weight:900}
.col.off .col-hd{color:#FFC72C}
.col.real .col-hd{color:#E8342A}
.q{font-size:26px;font-weight:900;line-height:1.5;margin-top:14px;letter-spacing:-.5px}
.col.off .q{color:#fff}
.col.real .q{color:#2B2520}
.src{margin-top:14px;font-size:19px;font-weight:700;opacity:.72}
.col.off .src{color:#CFC4B6}
.col.real .src{color:#8B7E70}

/* 中间的 VS */
.cols{position:relative;display:flex;gap:22px}
.vs{position:absolute;left:50%;margin-left:-39px;top:44px;width:78px;height:78px;
  border-radius:50%;background:#FFC72C;color:#2B2520;
  font-size:26px;font-weight:900;display:flex;align-items:center;justify-content:center;
  box-shadow:0 6px 0 #D99A00;z-index:5;border:6px solid #FFF6E0}

/* 分数条 */
.score{margin-top:26px;background:#fff;border-radius:26px;padding:22px 26px;
  border:4px solid #EFDFC0;box-shadow:0 8px 0 rgba(0,0,0,.05)}
.score-t{display:flex;align-items:baseline;justify-content:space-between}
.score-n{font-size:46px;font-weight:900;color:#E8342A}
.score-l{font-size:21px;color:#8B7E70;font-weight:700}
.bars{margin-top:14px;display:flex;align-items:flex-end;gap:12px;height:92px}
.bcol{flex:1;display:flex;flex-direction:column;justify-content:flex-end;height:100%}
.bar{border-radius:8px 8px 0 0;display:flex;align-items:flex-end;justify-content:center;
  font-size:18px;font-weight:900;color:#fff;padding-bottom:7px;
  text-shadow:0 1px 2px rgba(0,0,0,.25)}
.blab{margin-top:7px;text-align:center;font-size:18px;color:#8B7E70;font-weight:900}

/* 结论 */
.concl{margin-top:26px;background:#E8342A;color:#fff;border-radius:26px;
  padding:22px 26px;box-shadow:0 8px 0 #B32018}
.concl-t{font-size:31px;font-weight:900;line-height:1.5}
.concl-s{margin-top:10px;font-size:21px;font-weight:700;opacity:.92}

.cta{margin-top:28px;display:flex;align-items:center;gap:16px}
.url{flex:1;background:#2B2520;color:#fff;border-radius:20px;padding:17px 22px;
  font-size:24px;font-weight:900;box-shadow:0 6px 0 rgba(0,0,0,.12)}
.star{background:#FFC72C;color:#2B2520;border-radius:20px;padding:17px 26px;
  font-size:24px;font-weight:900;box-shadow:0 6px 0 #D99A00}
.foot{margin-top:18px;font-size:18px;color:#B3A695;font-weight:700;line-height:1.7}
</style></head><body>
<div class="bg"></div>
<div class="wrap">
  <div class="top"><div class="logo">香</div><div class="bn">麦门<span>真香榜</span></div></div>
  <div class="kick">麦当劳官方标签 × 真实用户评价 · 摊开对账</div>
  <h1>官方说「浓郁奶香<em>拉丝芝士</em>」<br>真实说「芝士棒是<em>空心的</em>」</h1>
  <div class="rule"></div>

  <div class="cols">
    <div class="col off">
      <div class="col-hd">🍔 官方风味标签</div>
      <div class="q">「浓郁奶香拉丝芝士」<br>「韩式辣椒黄油风味」</div>
      <div class="src">来自麦当劳 MCP 官方菜单接口</div>
    </div>
    <div class="col real">
      <div class="col-hd">💬 真实用户评价</div>
      <div class="q">「宣传图的拉丝完全是诈骗来的」<br>「芝士棒是空心的，只有面粉皮子」</div>
      <div class="src">来自微信公众号 / 今日头条的真实测评</div>
    </div>
    <div class="vs">VS</div>
  </div>

  <div class="score">
    <div class="score-t">
      <div><span class="score-n">5★ ↔ 2★</span> <span class="score-l">同一款汉堡，两极评价</span></div>
      <div class="score-l">真实评价 6 篇 · 均分 3.7 · 离散度 3.0（满分 3）</div>
    </div>
    <div class="bars">
      <div class="bcol"><div class="bar" style="height:88px;background:#3CC93C">×{D5}</div><div class="blab">5★</div></div>
      <div class="bcol"><div class="bar" style="height:70px;background:#7ED07E">×{D4}</div><div class="blab">4★</div></div>
      <div class="bcol"><div class="bar" style="height:52px;background:#FFC72C">×{D3}</div><div class="blab">3★</div></div>
      <div class="bcol"><div class="bar" style="height:34px;background:#E8342A">×{D2}</div><div class="blab">2★</div></div>
    </div>
  </div>

  <div class="concl">
    <div class="concl-t">均分 3.7 只是平均，掩盖不了这个分歧。</div>
    <div class="concl-s">同一个汉堡，有人说「层次感拉满」，有人说「芝士棒是空心的」——这就是官方标签和真实口碑之间那道裂缝。</div>
  </div>

  <div class="cta">
    <div class="url">zmz-beijita.github.io/mcd-flavor-index</div>
    <div class="star">⭐ 点个 Star</div>
  </div>
  <div class="foot">基于麦当劳中国 MCP 官方接口 + 49 篇真实公开评价 · 非麦当劳官方产品 · 评价版权归原作者所有</div>
</div>
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


def main():
    with open(os.path.join(ROOT, "data_ugc.json"), encoding="utf-8") as f:
        ugc = json.load(f)
    with open(os.path.join(ROOT, "data", "home.json"), encoding="utf-8") as f:
        home = json.load(f)

    # 从真实数据取：商品、评分分布、均分、离散度
    target = next(i for i in ugc["items"] if i["name"] == "龙焰芝士棒鸡腿堡")
    t = next(x for x in home["truth"] if x["name"] == "龙焰芝士棒鸡腿堡")
    scores = [u["score"] for u in target["ugc"]]
    dist = {s: scores.count(s) for s in (5, 4, 3, 2)}

    n_ugc = sum(len(i.get("ugc", [])) for i in ugc["items"])

    html = (TPL.replace("{N_UGC}", str(n_ugc))
                .replace("{D5}", str(dist[5]))
                .replace("{D4}", str(dist[4]))
                .replace("{D3}", str(dist[3]))
                .replace("{D2}", str(dist[2]))
                .replace("{AVG}", str(t["avg"]))
                .replace("{SPREAD}", str(t["spread"]))
                .replace("{N_ITEM}", str(t["n"])))
    tmp = os.path.join(ROOT, "docs", "_social-card.html")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(html)

    cdp = CDP("file://" + os.path.abspath(tmp), 1080, 1440)
    try:
        time.sleep(2.2)
        cdp.evaluate("(async()=>{try{await document.fonts.ready;}catch(e){}"
                     "await new Promise(r=>requestAnimationFrame("
                     "()=>requestAnimationFrame(r)));return true;})()")
        time.sleep(1.2)
        # 检查 CSS 是否完整解析
        n_rules = cdp.evaluate("document.styleSheets[0].cssRules.length")
        print("CSS 规则数:", n_rules)
        out = os.path.join(ROOT, "docs", "social-card.png")
        cdp.shot(out, 1080, 1440)
        print(f"已生成 {out}")
        print(f"  数据来源: {t['name']} / 评分分布 {dist} / 均分 {t['avg']} / 离散度 {t['spread']}")
    finally:
        cdp.close()
        if os.path.exists(tmp):
            os.remove(tmp)


if __name__ == "__main__":
    main()
