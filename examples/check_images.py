#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用真实浏览器逐个检查商品图是否真的加载出来。

背景：之前出现过「很多食物没有图片」的反馈。静态检查映射表不够——
必须让浏览器真的去请求每个 <img>，看 naturalWidth 是否 > 0。
本地图走 file:// 相对路径，远程图走 CDN，逐个统计。

用法：python examples/check_images.py index.html
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
        self.buf = b""
        while b"\r\n\r\n" not in self.buf:
            self.buf += self.sock.recv(4096)
        self.buf = b""
        self.mid = 0

    def _send(self, method, params):
        self.mid += 1
        mid = self.mid
        payload = json.dumps({"id": mid, "method": method,
                              "params": params}).encode()
        n = len(payload)
        hdr = f"81{0x80 | n:02x}"
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

    def close(self):
        try:
            self.sock.close()
        except Exception:
            pass
        self.proc.terminate()
        time.sleep(0.2)
        shutil.rmtree(self.prof, ignore_errors=True)


def main():
    html = sys.argv[1] if len(sys.argv) > 1 else "index.html"
    url = "file://" + os.path.abspath(html)
    cdp = CDP(url)
    try:
        time.sleep(2.5)
        # 人气榜默认只渲染前 20 个，先把 hotLimit 拉满，让全部商品进 DOM
        cdp.evaluate("""
        (()=>{ try{
            hotLimit = 9999;
            renderHot();
        }catch(e){ return 'ERR:'+e.message; }
        return 'ok'; })()
        """)
        time.sleep(1.2)
        # 触发懒加载：分段滚动到底
        cdp.evaluate("""
        (async()=>{
          const H=document.body.scrollHeight;
          for(let y=0;y<=H;y+=600){ window.scrollTo(0,y); await new Promise(r=>setTimeout(r,60)); }
          window.scrollTo(0,0);
          return true;
        })()
        """)
        time.sleep(2.5)

        res = cdp.evaluate("""
        (()=>{
          const imgs=[...document.querySelectorAll('img')];
          const broken=imgs.filter(i=>i.complete && i.naturalWidth===0)
                          .map(i=>i.getAttribute('src'));
          const placeholder=document.querySelectorAll('.rank-pic.none').length;
          return JSON.stringify({
            total: imgs.length,
            loaded: imgs.filter(i=>i.naturalWidth>0).length,
            broken: broken.slice(0,20),
            brokenCount: broken.length,
            placeholder
          });
        })()
        """)
        print(json.dumps(json.loads(res), ensure_ascii=False, indent=1))
    finally:
        cdp.close()


if __name__ == "__main__":
    main()
