# MCP 集成说明 · 麦门真香榜

> 本项目实际使用的麦当劳 MCP Server 调用方式、返回结构清洗规则、以及实测踩坑记录。
> 全部内容基于 **2026-10-25 对 `https://mcp.mcd.cn` 的真实调用**，非文档转述。

## 接入配置

```json
{
  "mcpServers": {
    "mcd-mcp": {
      "type": "streamablehttp",
      "url": "https://mcp.mcd.cn",
      "headers": {
        "Authorization": "Bearer YOUR_MCP_TOKEN"
      }
    }
  }
}
```

- 传输协议：Streamable HTTP
- Token 申请：<https://mcp.mcd.cn> → 手机号登录 → 控制台 → 激活
- 限流：每个 Token 每分钟最多 600 次请求，超限返回 `429`

## 实际调用的工具

| 工具 | 本项目用它做什么 | 关键返回字段 |
|---|---|---|
| `query-meals` | **官方风味标签**的唯一来源；拿在售商品与分类 | `data.categories[].meals[].tags`（实测 66 种官方风味词，菜单每日轮换）、`.code` |
| `query-meal-detail` | 套餐结构（rounds）、子项差价、**官方商品图地址** | `data.rounds[].choices[].diffPrice`、`data.image` |
| `calculate-price` | **唯一可信的价格来源** | `data.price`（单位：分）、`data.productList`、`data.takeWayList` |
| `query-nearby-stores` | 按位置搜门店 | `data[].storeCode`、`data[].storeName`、`data[].reservationTimeOptions` |
| `list-nutrition-foods` | 副维度：钠 / 蛋白 / 热量（160 条） | `data` 是**逗号分隔文本表格**，不是 JSON |
| `now-time-info` | 确认当前时间 | `data.formatted`、`data.dayOfWeek` |

未使用任何写操作（`create-order` / `cancel-order` / `auto-bind-coupons` / `mall-create-order` /
`party-order-create` / `delivery-create-address` / `draw-lottery` / `campaign-calendar` 等）。

## 官方风味标签：为什么这是本项目的关键

`query-meals` 返回的 `tags` 字段里，除了「人气」「单品」「套餐」这类通用分类标签，
还有一批**麦当劳官方自己标注的风味描述**：

```
浓郁奶香拉丝芝士 · 韩式辣椒黄油风味 · 心形薯饼同款比心 · 趁热拉丝 · 奶香醇厚
口口酥脆 · 板烧滋滋 · 多汁惹味 · 浓郁咖喱飘香 · 大口吃肉好快乐
蘸酱炸鸡新吃法 · 浓郁芝香 · 使用动物奶油 · 汪苏泷限量周边 · 既可捶背又可挠痒
```

这些标签是**麦当劳自己写的**，不是第三方推测。它们的可溯源性和时效性（每天随菜单接口更新）
是本项目与同赛道项目（手工标注口味图谱）的核心差异。

**清洗规则**：过滤掉「人气」「单品」「套餐」「小食」「冷饮」「热饮」等通用分类词，
只保留描述风味或产品特征的标签。

## 价格处理

- `calculate-price` 返回的价格**单位是分**，展示时除以 100
- `query-meal-detail` 里**没有价格字段**，任何价格都必须走 `calculate-price`
- `data.price` 是最终应付；`data.productPrice` 是商品原价；`data.discount` 是优惠金额
- `data.takeWayList` 给出可选取餐方式（如 `locker-out` 外带 / 店外取餐柜），
  到店下单时需要携带 `takeWayCode`

## ⚠️ 八条实测踩坑（全部可复现）

### 1. `calculate-price` 的 `roundList` 里 `round` 必须传 round 的 id

传中文名会直接返回「服务器发生了未知的问题」：

```jsonc
// ❌ 服务端 500
{"round": "主食任意选", "comboItemList": [{"code": "1406", "quantity": 1}]}

// ✅ 正常
{"round": "1", "comboItemList": [{"code": "1406", "quantity": 1}]}
```

`round` 的 id 来自 `query-meal-detail` 返回的 `data.rounds[].id`。
**这是 MCP 文档里没写清的隐式约定，所有做套餐换购的项目都会踩。**

### 2. 门店搜索 `searchType` 必须是 2

```jsonc
{"beType": 1, "searchType": 1}   // ❌ 只查收藏餐厅，新用户拿到「收藏餐厅列表为空」
{"beType": 1, "searchType": 2, "city": "上海", "keyword": "人民广场"}  // ✅ 按位置搜
```

### 3. 返回体不是纯 JSON

MCP 的 `result.content[].text` 里塞的是 Markdown 说明 + 真实 JSON，真实数据在
`## Original Response` 之后。`mcd_client.py` 已处理（优先读 `structuredContent`，
回退时解析 `## Original Response` 段）。

### 4. `list-nutrition-foods` 的 data 是逗号分隔文本表格

```
[160]{productName,nutritionDescription,energyKj,energyKcal,protein,fat,carbohydrate,sodium,calcium}:
  猪柳麦满分,null,1288,308,16,16,24,781,213
```

`nutrition_index.py` 负责解析与对齐。**对齐不上时必须返回 None 并标注"数据缺失"，
不能拿邻近条目凑数。**

### 5. 商品编码每天会变

同一商品编码隔天可能失效。实测「人气经典随心配」的编码从 `9900013304` 变成了 `9900015187`，
「龙焰鸡腿堡」的 `1440` 在某次调用中返回 `code=60001 未匹配到商品`。
**不要硬编码 productCode，要先拉 `query-meals` 再按名称反查。**

### 6. 菜单里有 ≠ 卖得了

实测 121 个菜单编码中，仅 107 个能核价成功，其余返回空数据（售罄或不可售）。

### 7. 核价返回 0 不等于免费

单独核价 `可乐中杯(3050)`、`无糖可口可乐中杯(3071)` 会返回：

```json
{"productOriginalPrice": 0, "price": 0, "productList": []}
```

`productList` 为空说明**该商品不能脱离套餐单独点**，不是免费。
若把它当成 0 元，"单点 vs 套餐"的比价结论会完全错。
`menu_solver.py` 的 `price_of()` 对此显式抛错。

### 8. 部分门店此刻暂停营业

核价会返回 `code=60003 门店暂停营业，请重新选择门店`。
实测同一关键词下 3 家门店有 2 家处于此状态，**搜到的门店不代表当下能下单**。

## 名称对齐规则

菜单商品名与营养库条目的命名不一致，`nutrition_index.py` 的对齐策略：

1. NFKC 归一化（统一全半角）
2. 去除括号补充说明：`100% 苹果汁(盒装)` → `100% 苹果汁`
3. 去标点与品牌符号：`麦咖啡™冰美式中杯` → `麦咖啡冰美式中杯`
4. 生成候选变体：`5块心形薯饼+韩式辣椒黄油风味酱` → `5块心形薯饼`；
   `麦咖啡冰美式中杯` → `冰美式中杯`；`大杯玉米杯` → `玉米杯`
5. 前缀匹配兜底（长度差 ≤ 3）

**匹配失败时返回 `(None, None)`，由上层标注"官方营养库未收录"。**
实测 101 个在售组件中 37 个（龙焰系列、麦炫酷、心形薯饼等新品）无营养数据。

## 数据来源（评价）

真香指数的原料是**真实公开用户评价**，采集于 2026-10-25，来源为：

- 小红书
- 什么值得买
- 大众点评
- 微信公众号（美食测评号）
- 今日头条
- 现食研（独立食品测评）

采集方式与口径见 [`references/ugc-collection.md`](references/ugc-collection.md)。

**评价原文版权归原作者所有**，本项目仅作短引用与统计，并标注来源。

## 不做的事

- 不下任何写操作
- 不虚构评价、来源、评分
- 不手工标注官方风味标签（只读接口返回）
- 不猜测商品编码（先拉菜单再反查）
- 不把 `price=0` 当成免费
