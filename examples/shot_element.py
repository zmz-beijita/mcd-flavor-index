#!/usr/bin/env python3
"""用 CDP 精确截取页面某个元素区域。

用法: python shot_element.py <html> <element_id> <out.png> [点击的筛选按钮 data-f]
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
            [CHROME, "--headless=new",
             f"--remote-debugging-port={self.port}",
             f"--user-data-dir={self.prof}", "--no-first-run", "--disable-gpu",
             f"--window-size={width},{height}", url],
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
             f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n"
             ).encode())
        buf = b""
        while b"\r\n\r\n" not in buf:
            buf += self.sock.recv(4096)
        self._id = 0

    def _send(self, method, params):
        self._id += 1
        mid = self._id
        data = json.dumps({"id": mid, "method": method,
                           "params": params}).encode()
        n = len(data)
        mask = os.urandom(4)
        hdr = bytearray([0x81])
        if n < 126:
            hdr.append(0x80 | n)
        elif n < 65536:
            hdr.append(0x80 | 126)
            hdr += n.to_bytes(2, "big")
        else:
            hdr.append(0x80 | 127)
            hdr += n.to_bytes(8, "big")
        hdr += mask
        hdr += bytes(b ^ mask[i % 4] for i, b in enumerate(data))
        self.sock.sendall(bytes(hdr))
        while True:
            hh = self.sock.recv(2)
            ln = hh[1] & 0x7F
            if ln == 126:
                ln = int.from_bytes(self.sock.recv(2), "big")
            elif ln == 127:
                ln = int.from_bytes(self.sock.recv(8), "big")
            p = b""
            while len(p) < ln:
                p += self.sock.recv(ln - len(p))
            m = json.loads(p)
            if m.get("id") == mid:
                return m

    def evaluate(self, expr):
        r = self._send("Runtime.evaluate",
                       {"expression": expr, "returnByValue": True})
        return r.get("result", {}).get("result", {}).get("value")

    def shot(self, clip, out):
        params = {"format": "png", "captureBeyondViewport": True}
        params["clip"] = {"x": float(clip["x"]), "y": float(clip["y"]),
                          "width": float(clip["width"]),
                          "height": float(clip["height"]),
                          "scale": 1}
        r = self._send("Page.captureScreenshot", params)
        data = r.get("result", {}).get("data")
        if not data:
            raise SystemExit("截图失败：" + json.dumps(r, ensure_ascii=False)[:300])
        with open(out, "wb") as f:
            f.write(base64.b64decode(data))
        return out

    def close(self):
        try:
            self.sock.close()
        except Exception:
            pass
        self.proc.terminate()
        time.sleep(0.2)
        shutil.rmtree(self.prof, ignore_errors=True)


def main():
    """用法: python shot_element.py <html> <目标> <out.png> [筛选按钮data-f] [点击选择器]

    <目标> 可以是元素 id，也可以是 CSS 选择器（以 # / . 开头时按选择器处理）。
    """
    html, elem_id, out = sys.argv[1], sys.argv[2], sys.argv[3]
    click_filter = sys.argv[4] if len(sys.argv) > 4 else None
    click_selector = sys.argv[5] if len(sys.argv) > 5 else None
    url = "file://" + os.path.abspath(html)
    cdp = CDP(url)
    try:
        time.sleep(2.5)
        if click_filter:
            cdp.evaluate(
                f'document.querySelector(\'[data-f="{click_filter}"]\').click()')
            time.sleep(0.6)
        if click_selector:
            cdp.evaluate(f'document.querySelector(\'{click_selector}\').click()')
            time.sleep(0.8)
        # js: 参数存在时先执行一段 JS（用于展开详情等前置动作）
        if len(sys.argv) > 6 and sys.argv[6]:
            cdp.evaluate(sys.argv[6])
            time.sleep(1.0)
        # 目标定位：
        #   js:<表达式>     → 表达式返回的元素（最灵活，能处理中文 id）
        #   #x / .x        → CSS 选择器
        #   其它            → 当作元素 id
        if elem_id.startswith("js:"):
            expr = elem_id[3:]
            sel = "(" + expr + ")"
        elif elem_id.startswith("#") or elem_id.startswith("."):
            sel = "document.querySelector('" + elem_id + "')"
        else:
            sel = 'document.getElementById("' + elem_id + '")'
        box = json.loads(cdp.evaluate(
            f'(()=>{{const e={sel};'
            f'if(!e) return JSON.stringify({{err:"找不到元素 {elem_id}"}});'
            f'const r=e.getBoundingClientRect();'
            f'return JSON.stringify({{x:Math.max(0,r.left-24),'
            f'y:Math.max(0,r.top+window.scrollY-24),'
            f'width:Math.min(1440,r.width+48),'
            f'height:e.offsetHeight+48,scale:1}})}})()'))
        if "err" in box:
            raise SystemExit("截图失败：" + box["err"])
        cdp.shot({"x": box["x"], "y": box["y"],
                  "width": box["width"], "height": box["height"]}, out)
        print(f"已保存 {out}  ({int(box['width'])}x{int(box['height'])})")
    finally:
        cdp.close()


if __name__ == "__main__":
    main()
