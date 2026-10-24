"""麦当劳 MCP 极简客户端（Streamable HTTP）。

只依赖标准库，无需 pip 安装。所有配置走环境变量：
  MCD_MCP_TOKEN  必填，麦当劳 MCP Token
  MCD_MCP_URL    可选，默认 https://mcp.mcd.cn

用法:
  from mcd_client import McdClient
  c = McdClient()
  c.call("now-time-info", {})
  c.list_tools()
"""

import json
import os
import urllib.error
import urllib.request

DEFAULT_URL = "https://mcp.mcd.cn"
PROTOCOL_VERSION = "2025-06-18"


class McdError(RuntimeError):
    """MCP 调用失败（含业务错误码）。"""


class McdClient:
    def __init__(self, token=None, url=None, timeout=60):
        self.token = token or os.environ.get("MCD_MCP_TOKEN", "")
        self.url = url or os.environ.get("MCD_MCP_URL", DEFAULT_URL)
        self.timeout = timeout
        self._session_id = None
        self._tools_cache = None
        if not self.token:
            raise McdError(
                "缺少 MCD_MCP_TOKEN。请设置环境变量："
                "export MCD_MCP_TOKEN='你的token'（Windows: set MCD_MCP_TOKEN=...）"
            )

    # ---------- 底层传输 ----------

    def _post(self, payload):
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self._session_id:
            headers["Mcp-Session-Id"] = self._session_id
        req = urllib.request.Request(
            self.url, data=json.dumps(payload).encode("utf-8"),
            headers=headers, method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                sid = resp.headers.get("Mcp-Session-Id")
                body = resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:300]
            raise McdError(f"HTTP {e.code}：{detail}") from e
        except urllib.error.URLError as e:
            raise McdError(f"网络不可达：{e.reason}") from e
        if sid:
            self._session_id = sid
        return self._parse(body)

    @staticmethod
    def _parse(body):
        body = body.strip()
        if not body:
            return {}
        if body.startswith("{"):
            return json.loads(body)
        for line in body.splitlines():
            if line.startswith("data:"):
                chunk = line[5:].strip()
                if chunk:
                    return json.loads(chunk)
        raise McdError(f"无法解析响应：{body[:300]}")

    # ---------- 会话 ----------

    def _ensure_session(self):
        if self._session_id is not None:
            return
        self._post({
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "mcd-sodium", "version": "1.0.0"},
            },
        })
        # 通知初始化完成（服务端可能不返回 body）
        try:
            self._post({
                "jsonrpc": "2.0", "method": "notifications/initialized",
                "params": {},
            })
        except McdError:
            pass

    # ---------- 公开 API ----------

    def list_tools(self):
        """返回全部工具的 inputSchema 摘要。"""
        if self._tools_cache is not None:
            return self._tools_cache
        self._ensure_session()
        resp = self._post({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        tools = resp.get("result", {}).get("tools", [])
        self._tools_cache = {
            t["name"]: {
                "description": t.get("description", ""),
                "required": t.get("inputSchema", {}).get("required", []),
                "properties": list(t.get("inputSchema", {}).get("properties", {}).keys()),
            }
            for t in tools
        }
        return self._tools_cache

    def call(self, tool, args=None, raw=False):
        """调用一个 MCP 工具。

        返回业务层 data（dict / list / str）。
        若业务 success=false，抛 McdError 并带上 code/message。
        raw=True 时返回完整 JSON-RPC 响应。
        """
        self._ensure_session()
        resp = self._post({
            "jsonrpc": "2.0", "id": 2, "method": "tools/call",
            "params": {"name": tool, "arguments": args or {}},
        })
        if raw:
            return resp

        if "error" in resp:
            raise McdError(f"{tool} 调用失败：{resp['error']}")

        result = resp.get("result", {})
        # 优先用 structuredContent（已是结构化 JSON）
        structured = result.get("structuredContent")
        if isinstance(structured, dict) and "success" in structured:
            if not structured.get("success"):
                raise McdError(
                    f"{tool} 业务失败（code={structured.get('code')}）："
                    f"{structured.get('message')}"
                )
            data = structured.get("data")
            # 空 data 是真实存在的业务状态（例：商品售罄时 calculate-price 返回
            # success=true 但 data={}）。静默返回 None 会让上层算出错误价格，
            # 所以这里显式区分「空结果」和「有数据」。
            if data is None:
                raise McdError(f"{tool} 返回成功但 data 为空（可能是商品不可售）")
            return data

        # 回退：解析 content[].text 里附带的原始 JSON
        text = ""
        for block in result.get("content", []):
            if block.get("type") == "text":
                text += block.get("text", "")
        if "## Original Response" in text:
            raw_json = text.split("## Original Response", 1)[1].strip()
            end = raw_json.rfind("}")
            if end > 0:
                try:
                    parsed = json.loads(raw_json[: end + 1])
                    if isinstance(parsed, dict) and "success" in parsed:
                        if not parsed.get("success"):
                            raise McdError(
                                f"{tool} 业务失败（code={parsed.get('code')}）："
                                f"{parsed.get('message')}"
                            )
                        return parsed.get("data")
                except json.JSONDecodeError:
                    pass
        if result.get("isError"):
            raise McdError(f"{tool} 返回错误：{text[:300]}")
        return result.get("content")


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    cli = McdClient()
    if sys.argv[1] == "--list":
        for name, meta in cli.list_tools().items():
            req = ",".join(meta["required"]) or "-"
            print(f"{name}({req})")
    else:
        args = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
        print(json.dumps(cli.call(sys.argv[1], args), ensure_ascii=False, indent=2))
