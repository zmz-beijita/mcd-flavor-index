# 需要手动操作的事（API 权限受限 / 安全）

> 原因：当前 PAT（fine-grained）在 `M-China` 组织仓库只有 READ 权限，
> 读到公开 issue 可以，写入被拒（403 `Resource not accessible by personal access token`）。
> 仓库自身的读写权限是有的。

---

## 一、把 Issue #1325 的正文改成纯链接 ✅ 已完成（2026-10-25 13:47）

**为什么做**：官方在 README 里提示「项目地址链接暂不要使用 Markdown 格式组织文本」。
我们最初用 Markdown 写的（`[url](url)`），已改为纯文本 URL。

**已验证（用 API 读存储的源文本）**：
```
项目地址：https://github.com/zmz-beijita/mcd-flavor-index
```
- 含 Markdown 语法 `](` → **False** ✅
- 是纯文本 URL → **True** ✅

> ⚠️ **注意**：GitHub 对裸 URL 会做 autolink（自动链接），
> 所以页面上**仍显示为蓝色可点链接** —— 这是 GitHub 的渲染行为，与是否用了
> Markdown 语法无关。官方要求的是**存储的源文本格式**，不是显示效果。
> 改之前和改之后，显示看起来一样，但存储格式已经合规。

**编辑 body 没有触发重新校验**（编辑后官方回复仍在、state 仍为 open、无新增失败评论），
所以可以放心继续编辑。

### 还可以顺手改的：简介里的过期数字

Issue 简介目前写「34 篇」「44 种」，实际是 **49 篇 / 66 种**。
评委点进仓库一对照就会发现不一致。最终正文见
[`docs/ISSUE_BODY_FINAL.txt`](ISSUE_BODY_FINAL.txt)，可直接复制粘贴。

---

## 二、开启 GitHub Pages ✅ 已完成（2026-10-25 核实）

**已开启并验证可用**：

| 项 | 值 |
|---|---|
| 状态 | `built` |
| 地址 | https://zmz-beijita.github.io/mcd-flavor-index/ |
| 分支 / 目录 | `master` / `/ (root)` |
| HTTP | 200 |

**无需再操作。** 若将来要重置：
Settings → Pages → Source 选 `Deploy from a branch` → Branch `master` → 目录 `/ (root)` → Save。

---

## 三、赛后轮换两个 Token（安全）

对话里出现过明文 Token，建议赛后轮换：
- 麦当劳 MCP Token：`wG9FZ2...`
- GitHub PAT：`github_pat_57CZ...`

**本仓库内已扫描确认：零 Token 泄露。**
- `mcp-config.example.json` 用的是 `${MCD_MCP_TOKEN}` 环境变量占位符
- 本地凭据写在 `.env.local`，已被 `.gitignore` 忽略；推送脚本 `examples/push_via_api.py`
  显式跳过 `.env` / `.env.local`，不会误传

> 赛后请同时轮换：GitHub PAT（Settings → Developer settings → Personal access tokens）
> 与麦当劳 MCP Token（赛事官方渠道）。
