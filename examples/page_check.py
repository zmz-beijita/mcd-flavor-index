"""页面体检：检查图片加载、横向溢出、空容器、过小文字。
用法：python check_pages.py <html文件列表...>
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

EXPR = r'''JSON.stringify({
  broken: Array.from(document.querySelectorAll("img")).filter(i=>i.naturalWidth===0).map(i=>i.src.split("/").pop()),
  imgTotal: document.querySelectorAll("img").length,
  overflowX: document.documentElement.scrollWidth > window.innerWidth + 2,
  overflowing: Array.from(document.querySelectorAll("*")).filter(el=>{
    const b=el.getBoundingClientRect();
    return b.width>0&&b.height>0&&(b.right>window.innerWidth+4||b.left<-4);
  }).slice(0,4).map(el=>el.tagName+"."+String(el.className).slice(0,20)),
  tiny: Array.from(document.querySelectorAll("p,li,td,span,div,a,button,h1,h2,h3")).filter(el=>{
    if(el.children.length||!el.textContent.trim())return false;
    return parseFloat(getComputedStyle(el).fontSize)<10;
  }).length,
  empty: ["ax-a","ax-c","bars-b","rank","spec","band","cmt-body","pol","pts"].filter(id=>{
    const e=document.getElementById(id); return e && e.children.length===0;
  }),
  textLen: document.body.innerText.length
})'''


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def evaluate(page_url, width, height):
    port = free_port()
    prof = tempfile.mkdtemp()
    proc = subprocess.Popen(
        [CHROME, "--headless=new", f"--remote-debugging-port={port}",
         f"--user-data-dir={prof}", "--no-first-run", "--disable-gpu",
         f"--window-size={width},{height}", page_url],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        ws = None
        for _ in range(60):
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
        if not ws:
            return {"error": "no devtools"}
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

        def send(m):
            data = json.dumps(m).encode()
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

        def recv():
            hh = sock.recv(2)
            ln = hh[1] & 0x7F
            if ln == 126:
                ln = int.from_bytes(sock.recv(2), "big")
            elif ln == 127:
                ln = int.from_bytes(sock.recv(8), "big")
            p = b""
            while len(p) < ln:
                p += sock.recv(ln - len(p))
            return json.loads(p)

        send({"id": 1, "method": "Runtime.evaluate",
              "params": {"expression": "document.readyState", "returnByValue": True}})
        # 等页面真正就绪
        for _ in range(50):
            msg = recv()
            if msg and msg.get("id") == 1:
                break
            time.sleep(0.05)
        time.sleep(0.8)

        send({"id": 2, "method": "Runtime.evaluate",
              "params": {"expression": EXPR, "returnByValue": True}})
        msg = None
        for _ in range(40):
            m = recv()
            if m and m.get("id") == 2:
                msg = m
                break
        sock.close()
        if not msg:
            return {"error": "no response"}
        res = msg.get("result", {})
        if "value" not in res:
            return {"error": json.dumps(res, ensure_ascii=False)[:200]}
        val = res["value"]
        if isinstance(val, str):
            return json.loads(val)
        return val
    finally:
        proc.terminate()
        time.sleep(0.2)
        shutil.rmtree(prof, ignore_errors=True)


def main():
    files = sys.argv[1:]
    if not files:
        print(__doc__)
        return
    for f in files:
        url = "file://" + os.path.abspath(f)
        for w, h in [(1440, 900), (375, 812)]:
            r = evaluate(url, w, h)
            print(f"=== {os.path.basename(f)} @ {w}x{h} ===")
            if "error" in r:
                print("   ERROR:", r["error"])
                continue
            print(f"   图片 {r['imgTotal'] - len(r['broken'])}/{r['imgTotal']}"
                  f"  坏图={r['broken']}")
            print(f"   横向溢出={r['overflowX']}  溢出元素={r['overflowing']}")
            print(f"   空容器={r['empty']}  <10px文字={r['tiny']}  正文长度={r['textLen']}")


if __name__ == "__main__":
    main()
