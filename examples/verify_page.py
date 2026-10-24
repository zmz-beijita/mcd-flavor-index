#!/usr/bin/env python3
"""页面功能验证：展开、投票、投稿、筛选、溢出。

用法：python verify_page.py [html文件]
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
    def __init__(self, url, width=1440, height=1000):
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

    def ev(self, expr):
        r = self._send("Runtime.evaluate",
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


def main():
    html = sys.argv[1] if len(sys.argv) > 1 else "index.html"
    url = "file://" + os.path.abspath(html)
    cdp = CDP(url)
    ok = True
    try:
        time.sleep(2.5)
        print("数据:", cdp.ev(
            "JSON.stringify({truth:DATA.truth.length,hot:DATA.hot.length,"
            "items:document.querySelectorAll('.rank-item').length,"
            "imgs:document.querySelectorAll('.rank-pic img').length})"))

        r = cdp.ev(r"""JSON.stringify((()=>{
          const bad=[];
          [...document.querySelectorAll('#truthList .rank-item')].forEach(r=>{
            const nm=r.querySelector('.rank-name').textContent.trim();
            r.querySelector('.rank-row').click();
            const it=document.querySelector('.rank-item.open');
            if(!it){bad.push(nm+' 未展开');return;}
            const d=it.querySelector('.detail');
            if(!d){bad.push(nm+' 无detail');return;}
            if(/undefined|NaN|\[object Object\]/.test(d.innerText))bad.push(nm+' 含undefined');
            [['投票区','.d-vote'],['输入框','.d-vote textarea'],['官方标签','.d-official'],
             ['真实共识','.d-real'],['离散度','.d-spread'],['评价原文','.d-ugc']
            ].forEach(p=>{if(!it.querySelector(p[1]))bad.push(nm+' 无'+p[0]);});
            it.querySelector('.rank-row').click();
          });
          return {bad};
        })())""")
        d = json.loads(r) if isinstance(r, str) else r
        print("展开验证:", "✅ 全部通过" if not d["bad"] else d["bad"])
        ok = ok and not d["bad"]

        r = cdp.ev(r"""JSON.stringify((()=>{
          const row=document.querySelector('#truthList .rank-item');
          row.querySelector('.rank-row').click();
          const it=document.querySelector('.rank-item.open');
          const nm=it.querySelector('.rank-name').textContent.trim();
          it.querySelector('.vb').click();
          const ta=it.querySelector('.d-vote textarea');
          ta.value='测试理由：这顿真的不错';
          ta.dispatchEvent(new Event('input',{bubbles:true}));
          const btn=it.querySelector('.vform button');
          btn.click();
          const posts=JSON.parse(localStorage.getItem('mcd_flavor_posts_v1')||'[]');
          const votes=JSON.parse(localStorage.getItem('mcd_flavor_votes_v1')||'{}');
          return {nm, posts:posts.length, votes:Object.keys(votes).length,
            postText:posts[0]?posts[0].text:'',
            voteKey:votes[nm]?votes[nm].vote:'',
            voteReason:votes[nm]?votes[nm].reason:''};
        })())""")
        d = json.loads(r) if isinstance(r, str) else r
        print("投票投稿:", json.dumps(d, ensure_ascii=False))
        ok = ok and d.get("posts", 0) > 0

        r = cdp.ev(r"""JSON.stringify((()=>{
          const out={};
          ['all','good','bad'].forEach(f=>{
            document.querySelector('[data-f="'+f+'"]').click();
            const items=[...document.querySelectorAll('#clist .ci')];
            out[f]={n:items.length, ok: f==='all'? items.length>0 : items.every(i=>{
              const sc=parseFloat(i.querySelector('.ubadge .s').textContent.trim());
              return f==='good'? sc>=4.5 : sc<=3.0;})};
          });
          const mine=document.querySelectorAll('#clist .ci.mine').length;
          return {out, mine};
        })())""")
        d = json.loads(r) if isinstance(r, str) else r
        print("筛选:", json.dumps(d, ensure_ascii=False))
        for k, v in d["out"].items():
            ok = ok and v["ok"]

        r = cdp.ev(r"""JSON.stringify((()=>{
          const ov=[];
          document.querySelectorAll('*').forEach(el=>{const b=el.getBoundingClientRect();
            if(b.width>0&&b.height>0&&(b.right>window.innerWidth+4||b.left<-4))
              ov.push(el.tagName+'.'+String(el.className).slice(0,24));});
          const tiny=[];
          document.querySelectorAll('p,li,span,div,a,button,textarea').forEach(el=>{
            if(el.children.length||!el.textContent.trim())return;
            if(parseFloat(getComputedStyle(el).fontSize)<10) tiny.push(el.className);});
          return {overflow:ov.length, ovList:ov.slice(0,5), tiny:tiny.length};
        })())""")
        d = json.loads(r) if isinstance(r, str) else r
        print("溢出/小字:", json.dumps(d, ensure_ascii=False))
        ok = ok and d["overflow"] == 0

        print("\n结论:", "✅ 全部通过" if ok else "❌ 有问题")
    finally:
        cdp.close()


if __name__ == "__main__":
    main()
