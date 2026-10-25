# 麦门真香榜 · McDonald's Flavor Index

<p align="center">
  <img src="docs/social-preview.png" width="100%" alt="官方说的 vs 大家说的：麦当劳真实口碑对账器">
</p>

> ## 官方说「浓郁奶香拉丝芝士」
> ## 真实评价说「宣传图的拉丝完全是诈骗来的」
>
> **同一个汉堡，5 星和 2 星同时存在。** 麦当劳菜单接口和真实用户口碑之间那道裂缝，
> 就是这个项目要量出来的东西。

[![MCD FLAVOR INDEX](https://img.shields.io/badge/MCD-FLAVOR%20INDEX-DA291C?style=flat-square)](https://github.com/zmz-beijita/mcd-flavor-index)
[![MCP](https://img.shields.io/badge/MCP-mcp.mcd.cn-FFC72C?style=flat-square)](https://mcp.mcd.cn)
[![零依赖](https://img.shields.io/badge/dependencies-stdlib%20only-brightgreen?style=flat-square)](#-免-token-打开即玩)
[![免Token体验](https://img.shields.io/badge/体验-免%20Token-orange?style=flat-square)](#-免-token-打开即玩)

**49 篇真实评价 · 9 款在售商品 · 96 个当前在售 · 官方标签落差逐条对账**

麦当劳程序员创意开发大赛参赛作品 · 非麦当劳官方产品

---

## 🎬 30 秒看懂

<img src="docs/screenshot-hero.png" width="100%" alt="麦门真香榜首页：真香榜为主体，凸起按钮，可点商品卡展开详情与投票">

**打开就能玩，什么都不用装、不用填 Token。** 点商品卡展开：官方风味标签 ↔ 真实共识对照、
官方配料清单、评分离散度条、评价原文，**还有一个能投票写理由的评论区**。

## 🏆 真香榜（按真实评价均分排序）

| 排名 | 商品 | 真香指数 | 评分区间 | 样本 | 官方核价 | 官方风味标签 |
|:--:|---|:--:|:--:|:--:|:--:|---|
| 1 | 双层吉士汉堡 | **4.4** | 3.0–5.0 | n=5 | ¥23.00 | 100%纯牛肉 / 人气 |
| 2 | 板烧鸡腿堡 | **4.3** | 3.0–5.0 | n=7 | ¥23.50 | 板烧滋滋 / 多汁惹味 |
| 3 | 麦辣鸡腿堡 | **4.3** | 3.0–5.0 | n=6 | ¥22.50 | 人气 / 人气经典 |
| 4 | 安格斯厚牛堡 | **4.2** | 3.0–5.0 | n=4 | ¥31.50 | 100%纯牛肉 / 安格斯MAX |
| 5 | 巨无霸 | **4.0** | 3.0–5.0 | n=9 | ¥25.50 | 100%纯牛肉 / 人气 |
| 6 | 麦香鱼 | **4.0** | 3.0–5.0 | n=4 | ¥25.50 | 100%纯牛肉 / 麦香鱼 |
| 7 | 龙焰芝士棒鸡腿堡 | **3.7** | 2.0–5.0 | n=6 | ¥29.90 | 浓郁奶香拉丝芝士 / 韩式辣椒黄油风味 |
| 8 | 麦香鸡汉堡 | **3.5** | 3.0–4.0 | n=4 | ¥17.00 | 人气 / 单炸鸡类 |
| 9 | 不素之霸双层牛堡 | **3.2** | 2.0–4.0 | n=4 | ¥26.50 | 100%纯牛肉 / 人气 |

**为什么龙焰芝士棒排倒数第一？** 它的官方标签写着「浓郁奶香拉丝芝士」「趁热拉丝」，
但 6 篇真实评价里有人说「层次感拉满」，有人说「芝士棒是空心的，只有面粉皮子」——
**评分离散度 3.0（满分 3），全榜分歧最大。** 均分 3.7 只是平均，掩盖不了这个分歧。

<img src="docs/screenshot-rank.png" width="100%" alt="真香榜：排名号、真香指数、样本量、评分区间、官方风味标签、分歧标记">

## ✍️ 麦门广场：你能投票，也能写理由

<img src="docs/screenshot-detail.png" width="100%" alt="展开详情：官方风味标签与真实共识对账、官方配料清单、评分离散度条、投票区、评价原文">

每个商品都能投 **真香 / 一般 / 踩雷**，并写一句理由（≤60 字），发到广场。

**理由才是可传播的内容。** 麦门已有的梗就是这么来的：

> 「宣传图的拉丝完全是诈骗来的」
> 「两根没有奶酪的芝士棒在麦当劳值三块钱」
> 「芝士棒是空心的，只有面粉皮子」

投票与投稿存在浏览器本地，不上传。

## 📋 人气榜（当前时段在售全量）

**96 个商品**，覆盖门店当前在售的每一项，按品类与官方销量信号排序。
有真实评价的显示真香分，没有的标「待评价」——你投完，它就成了真香分。

> 麦当劳菜单**每日轮换**（凌晨切早餐、上午切正餐），所以人气榜是「现在能点什么」，
> 真香榜是「历史上大家怎么说」。两个时间维度，两个用途。

## 📱 微信小程序版

同款数据的小程序实现，三个 Tab：**真香榜 / 麦门广场 / 我的**。
纯原生微信小程序，零 npm 依赖、零云服务，投票与投稿只存本机。源码见 [`miniprogram/`](miniprogram/)。

## 🔌 用了哪些 MCP 工具

| 工具 | 用途 |
|---|---|
| `query-meals` | **官方风味标签**（`tags` 字段，麦当劳自己写的）与在售分类 |
| `query-meal-detail` | **官方配料清单**（`modification`）与**官方套餐结构**（`rounds`，每一档能换什么） |
| `calculate-price` | **唯一可信的价格来源**（单位：分） |
| `query-nearby-stores` | 按位置搜门店（`searchType` 必须是 2） |
| `campaign-calendar` | 官方活动文案（新品描述、联名、优惠预告） |
| `list-nutrition-foods` | 158 条营养数据（副维度：钠 / 蛋白 / 热量） |
| `now-time-info` | 确认当前时间 |

详见 [`MCP_INTEGRATION.md`](skills/mcd-flavor-index/MCP_INTEGRATION.md)，含 **8 条实测踩坑记录**。

## 💡 为什么不是"又一个点餐助手"

| | 点餐助手 | 麦门真香榜 |
|---|---|---|
| 回答的问题 | 怎么点最省 | **官方说的和实际差多少** |
| 数据来源 | 菜单 + 券 | 菜单**官方标签** + **真实评价原文** |
| 是否需要消费记录 | 需要 | 不需要 |
| 产物 | 一个订单 | **可核查的口碑审计 + 可下单的方案** |
| 互动 | 无 | 投票 + 写理由 + 广场 |

**同赛道已有** `mcd-flavor-scout`（7 星，手工标 119 款口味）与 `mcd-mood-palette`（154 星，心情 × 营养打分）。
两者的口味数据都是**手工标注**的，不可溯源、不会更新。
本项目的官方标签**直接来自 MCP 接口、每日自动更新**，
并且多做一件没人做的事——**「官方 vs 真实」这道对账**。

## 📐 方法与边界

- **真香指数** = 该商品全部真实评价评分的算术平均（5 分制，采用各平台原生评分，未二次折算）
- **评分离散度** = 最高星 − 最低星，越大说明口碑越分裂
- **官方标签落差** = 官方标签声称的效果，是否被真实评价否定（关键词规则公开在 `build_home_data.py`，不做黑箱）
- 样本量与评分区间随商品一并公开，**样本少则可信度低**
- 评价原文版权归原作者所有，此处仅作短引用与统计

## 📁 目录结构

```
mcd-flavor-index/
├── index.html                    # 交互式真香榜（单文件，免 Token）
├── data_ugc.json                 # 49 篇真实评价原始数据（含来源与评分）
├── data/home.json                # 首页双榜数据（真香榜 6 + 人气榜 96）
├── data/menu_full.json           # 96 个在售商品的官方标签 / 配料 / 套餐结构
├── assets/mcd-brand/             # 官方商品图（来自 MCP 返回的 CDN 地址）
├── docs/                         # 截图与社交预览图
├── scripts/
│   ├── collect_menu.py            # 采集门店菜单全量官方信息
│   └── build_home_data.py         # 生成首页双榜数据
├── miniprogram/                  # 微信小程序版（原生，零依赖）
└── skills/mcd-flavor-index/
    ├── SKILL.md                  # Skill 主流程与铁律
    ├── MCP_INTEGRATION.md        # MCP 调用说明 + 8 条踩坑
    ├── CONTEST_DECLARATION.md    # 参赛声明（官方文件，未改动）
    ├── mcp-config.example.json   # 脱敏 MCP 配置
    ├── workbuddy.md              # WorkBuddy 开发上下文
    ├── scripts/
    │   ├── flavor_index.py       # 真香指数计算 + 页面生成
    │   ├── mcd_client.py         # MCP 客户端（含空数据防护）
    │   ├── nutrition_index.py    # 营养库解析与名称对齐
    │   └── menu_solver.py        # 菜单抓取 + 组合枚举
    └── references/
        └── ugc-collection.md     # 评价采集方法与口径
```

## 🚀 免 Token 打开即玩

```bash
git clone https://github.com/zmz-beijita/mcd-flavor-index.git
cd mcd-flavor-index
open index.html          # macOS
# Windows：直接双击 index.html
```

零依赖、零构建、单文件，图片已相对路径内嵌。

### 作为 WorkBuddy Skill 使用

```bash
cp -r skills/mcd-flavor-index ~/.workbuddy/skills/
```

在 WorkBuddy 左侧【专家·技能·连接器】→【自定义连接器】→【配置MCP】填入：

```json
{
  "mcpServers": {
    "mcd-mcp": {
      "type": "streamablehttp",
      "url": "https://mcp.mcd.cn",
      "headers": { "Authorization": "Bearer YOUR_MCP_TOKEN" }
    }
  }
}
```

保存并启用后，在对话里说「**麦当劳现在什么最值得吃**」即可。

```bash
export MCD_MCP_TOKEN=你的token

# 采集门店菜单全量官方信息（标签 / 配料 / 套餐结构 / 核价）
python scripts/collect_menu.py --store 1450713

# 重新生成首页数据与页面
python scripts/build_home_data.py
python skills/mcd-flavor-index/scripts/flavor_index.py --render
```

## 📄 许可证

MIT
