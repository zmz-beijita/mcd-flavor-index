# 需要手动操作的三件事（API 权限受限）

> 原因：当前 PAT（fine-grained）在 `M-China` 组织仓库只有 READ 权限，
> 读到公开 issue 可以，写入被拒（403 `Resource not accessible by personal access token`）。
> 仓库自身的读写权限是有的（已成功推送 117 个文件）。

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

## 二、开启 GitHub Pages（拿 Star 的关键）

**为什么做**：`mcd-party-planner`（1423 星）这类头部项目都有可点开的在线 demo。
GitHub 的社交预览图（`docs/social-preview.png`）也要 Pages 开启后才生效。

**操作**：
1. 打开仓库 https://github.com/zmz-beijita/mcd-flavor-index
2. 顶部菜单 **Settings** → 左侧 **Pages**
3. Source 选 **Deploy from a branch**
4. Branch 选 **master**，目录选 **/ (root)**
5. 点 **Save**

开启后：
- 主页：https://zmz-beijita.github.io/mcd-flavor-index/
- 社交预览图会显示在 Star 按钮右侧（社交分享到微信/微博时显示这张图）

**注意**：`index.html` 用 `fetch('data/home.json')`，Pages 上是 http 环境，fetch 正常。

---

## 三、赛后轮换两个 Token（安全）

对话里出现过明文 Token，建议赛后轮换：
- 麦当劳 MCP Token：`wG9FZ2...`
- GitHub PAT：`github_pat_57CZ...`

本仓库内已扫描确认：**零 Token 泄露**（`mcp-config.example.json` 用的是
`${MCD_MCP_TOKEN}` 环境变量占位符）。
