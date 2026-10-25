#!/usr/bin/env python3
"""用真实移动端视口（DeviceMetricsOverride）检查横向溢出。

无头浏览器的 --window-size 不等于 CSS 视口宽，必须用 Emulation 模拟真机。
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
    def __init__(self, url, width, height, mobile=True):
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
        self.send("Emulation.setDeviceMetricsOverride", {
            "width": width, "height": height,
            "deviceScaleFactor": 2, "mobile": mobile})

    def send(self, method, params):
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

    def ev(self, expr):
        r = self.send("Runtime.evaluate",
                      {"expression": expr, "returnByValue": True})
        return r.get("result", {}).get("result", {}).get("value")

    def close(self):
        try:
            self.sock.close()
        except Exception:
            pass
        self.proc.terminate()
        time.sleep(0.2)
        shutil.rmtree(self.prof, ignore_errors=True)


EXPR = '''JSON.stringify((()=>{
  const W=window.innerWidth;
  const wide=[];
  document.querySelectorAll("*").forEach(el=>{
    const b=el.getBoundingClientRect();
    if(b.width>W+2&&b.height>0) wide.push(el.tagName+"."+String(el.className).slice(0,26)+"|w="+Math.round(b.width));
  });
  return {viewport:W, docW:document.documentElement.scrollWidth, bodyW:document.body.scrollWidth,
          overflowing:wide.length, list:wide.slice(0,6)};
})())'''


def main():
    html = sys.argv[1] if len(sys.argv) > 1 else "index.html"
    url = "file://" + os.path.abspath(html)
    for w, h, label in [(375, 812, "iPhone SE/8"),
                        (390, 844, "iPhone 14"),
                        (768, 1024, "iPad 竖"),
                        (1440, 900, "桌面")]:
        cdp = CDP(url, w, h)
        try:
            time.sleep(2.2)
            v = cdp.ev(EXPR)
            d = json.loads(v) if isinstance(v, str) else v
            ok = d["docW"] <= w + 2
            print(f"{label:>12} {w}x{h}  视口={d['viewport']} 文档宽={d['docW']} "
                  f"溢出元素={d['overflowing']}  {'✅' if ok else '❌ 横向溢出'}")
            if not ok:
                for x in d["list"]:
                    print(f"                   └─ {x}")
        finally:
            cdp.close()


if __name__ == "__main__":
    main()
