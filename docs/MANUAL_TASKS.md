# 需要手动操作的事（API 权限受限 / 安全）

> 原因：当前 PAT（fine-grained）在 `M-China` 组织仓库只有 READ 权限，
> 读到公开 issue 可以，写入被拒（403 `Resource not accessible by personal access token`）。
> 仓库自身的读写权限是有的。

---

## 一、把 Issue #1325 的正文改成纯链接（可选，稳妥起见做）

**为什么做**：官方在 README 里提示「项目地址链接暂不要使用 Markdown 格式组织文本」。
GitHub 会把裸 URL 自动转成 `[url](url)`。虽然当前已报名成功，但改成纯文本更保险。

**操作**：
1. 打开 https://github.com/M-China/mcd-developer-innovation-challenge/issues/1325
2. 右上角 `⋯` → Edit
3. 把「项目地址」那一行改成纯文本：

```
项目地址：https://github.com/zmz-beijita/mcd-flavor-index
```

> ⚠️ GitHub 编辑时仍可能自动转成 Markdown。若转了，**不用管**——当前版本已通过官方校验，
> 官方回复「您的作品已成功参赛」，编辑反而可能触发重新校验。

**结论：建议不改。已报名成功，改动有触发重新校验的风险。**

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
