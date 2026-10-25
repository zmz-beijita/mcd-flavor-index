#!/usr/bin/env python3
"""扫描页面里所有可见文本节点中的 undefined / NaN / [object Object]。

覆盖：初始渲染、展开每个榜单条目、三档筛选。
用法：python scan_undefined.py [html文件]
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


EXPR = r'''JSON.stringify((()=>{
  const bad=[];
  const scan=(where)=>{
    document.querySelectorAll('*').forEach(el=>{
      if(el.children.length) return;
      const tag=el.tagName;
      if(tag==='SCRIPT'||tag==='STYLE') return;
      const t=(el.textContent||'').trim();
      if(!t) return;
      if(/undefined|NaN|\[object Object\]/.test(t))
        bad.push(where+' | '+tag+'.'+String(el.className).slice(0,20)+' | '+t.slice(0,50));
    });
  };
  scan('初始');
  const expandAll=(sel,limit)=>{
    [...document.querySelectorAll(sel)].slice(0,limit).forEach(r=>{
      const nm=r.querySelector('.rank-name').textContent.trim();
      r.querySelector('.rank-row').click();
      scan('展开:'+nm);
      const it=document.querySelector('.rank-item.open');
      if(it) it.querySelector('.rank-row').click();
    });
  };
  expandAll('#truthList .rank-item', 100);
  expandAll('#hotList .rank-item', 30);
  ['all','good','bad'].forEach(f=>{
    const b=document.querySelector('[data-f="'+f+'"]');
    if(b){b.click(); scan('筛选:'+f);}
  });
  return {bad};
})())'''


def main():
    html = sys.argv[1] if len(sys.argv) > 1 else "index.html"
    port = free_port()
    prof = tempfile.mkdtemp()
    proc = subprocess.Popen(
        [CHROME, "--headless=new", f"--remote-debugging-port={port}",
         f"--user-data-dir={prof}", "--no-first-run", "--disable-gpu",
         "--window-size=1440,1200", "file://" + os.path.abspath(html)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        ws = None
        for _ in range(80):
            try:
                d = json.load(urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/json", timeout=1))
                pg = [x for x in d if x.get("type") == "page"
                      and x.get("webSocketDebuggerUrl")]
                if pg:
                    ws = pg[0]["webSocketDebuggerUrl"]
                    break
            except Exception:
                time.sleep(0.2)
        host, path = ws.replace("ws://", "").split("/", 1)
        host, p2 = host.split(":")
        key = base64.b64encode(os.urandom(16)).decode()
        sock = socket.create_connection((host, int(p2)))
        sock.sendall(
            (f"GET /{path} HTTP/1.1\r\nHost: {host}:{p2}\r\n"
             f"Upgrade: websocket\r\nConnection: Upgrade\r\n"
             f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n"
             ).encode())
        buf = b""
        while b"\r\n\r\n" not in buf:
            buf += sock.recv(4096)
        mid = 1
        data = json.dumps({"id": mid, "method": "Runtime.evaluate",
                           "params": {"expression": EXPR,
                                      "returnByValue": True}}).encode()
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
        sock.sendall(bytes(hdr))
        msg = None
        while True:
            hh = sock.recv(2)
            ln = hh[1] & 0x7F
            if ln == 126:
                ln = int.from_bytes(sock.recv(2), "big")
            elif ln == 127:
                ln = int.from_bytes(sock.recv(8), "big")
            p = b""
            while len(p) < ln:
                p += sock.recv(ln - len(p))
            m = json.loads(p)
            if m.get("id") == mid:
                msg = m
                break
        sock.close()
        v = msg["result"]["result"].get("value")
        d = json.loads(v) if isinstance(v, str) else v
        bad = d.get("bad", [])
        print("undefined / NaN 节点数:", len(bad))
        for x in bad[:15]:
            print("  -", x)
        print("\n结论:", "✅ 无异常" if not bad else "❌ 需修复")
        sys.exit(0 if not bad else 1)
    finally:
        proc.terminate()
        time.sleep(0.2)
        shutil.rmtree(prof, ignore_errors=True)


if __name__ == "__main__":
    main()
