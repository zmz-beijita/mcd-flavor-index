"""菜单抓取与套餐组合求解。

把三份真实数据打通：
  1. query-meals      → 门店当前在售的分类与商品编码
  2. query-meal-detail→ 每个商品的套餐结构（rounds）、子项、差价、特制选项
  3. calculate-price  → 官方核价（唯一可信的价格来源，单位：分）
  4. list-nutrition-foods → 营养库（热量/蛋白/钠…）

关键坑（已实测）：calculate-price 的 roundList 里 round 字段必须传
round 的 id 字符串（如 "1"、"2"、"3"），传中文名会直接返回
"服务器发生了未知的问题"。本模块统一处理。
"""

import itertools
import json
import re
import time

from mcd_client import McdClient, McdError

# 差价字符串形如 "+ ¥2" / "- ¥1" / "+ ¥0.5" / "+ ¥0"
_DIFF = re.compile(r"([+-])\s*¥\s*([\d.]+)")


def parse_diff_price(text):
    """把 "+ ¥2" 解析成 2.0（单位：元）；无差价返回 0.0。"""
    if not text:
        return 0.0
    m = _DIFF.search(str(text))
    if not m:
        return 0.0
    sign = 1.0 if m.group(1) == "+" else -1.0
    return sign * float(m.group(2))


class MenuSnapshot:
    """某门店某一时刻的在售菜单快照。"""

    def __init__(self, client, store_code, order_type=1, be_type=1, be_code=None):
        self.client = client
        self.store_code = store_code
        self.order_type = order_type
        self.be_type = be_type
        self.be_code = be_code
        self.categories = []
        self.products = {}      # code -> {name, categories, tags, rounds, price}
        self.nutrition = None

    # ---------- 数据获取 ----------

    def _base_args(self):
        args = {
            "storeCode": self.store_code,
            "orderType": str(self.order_type),
            "beType": self.be_type,
        }
        if self.be_code:
            args["beCode"] = self.be_code
        return args

    def load_menu(self):
        """拉取在售菜单（分类 + 商品编码）。"""
        data = self.client.call("query-meals", self._base_args())
        self.categories = data.get("categories", []) if isinstance(data, dict) else []
        for cat in self.categories:
            for meal in cat.get("meals", []):
                code = meal.get("code")
                if not code:
                    continue
                p = self.products.setdefault(code, {
                    "code": code, "name": "", "categories": [],
                    "tags": [], "rounds": [], "price": None,
                })
                if cat.get("name"):
                    label = cat["name"].strip()
                    if label not in p["categories"]:
                        p["categories"].append(label)
                for t in meal.get("tags", []) or []:
                    if t not in p["tags"]:
                        p["tags"].append(t)
        return self

    def load_details(self, codes=None, workers=6):
        """批量拉取商品详情（套餐结构、子项差价、特制选项）。"""
        import concurrent.futures as cf

        targets = list(codes) if codes else list(self.products.keys())

        def fetch(code):
            try:
                return code, self.client.call("query-meal-detail",
                                              dict(self._base_args(), code=code))
            except McdError:
                return code, None

        with cf.ThreadPoolExecutor(max_workers=workers) as ex:
            for code, detail in ex.map(fetch, targets):
                if not detail:
                    continue
                p = self.products.setdefault(code, {
                    "code": code, "name": "", "categories": [],
                    "tags": [], "rounds": [], "price": None,
                })
                p["name"] = detail.get("name", "")
                p["rounds"] = detail.get("rounds", []) or []
        return self

    def load_prices(self, workers=6):
        """用 calculate-price 批量核价。单位：分。"""
        import concurrent.futures as cf

        def fetch(code):
            try:
                data = self.client.call("calculate-price", dict(
                    self._base_args(),
                    items=[{"productCode": code, "quantity": 1}],
                ))
                if isinstance(data, dict) and data.get("price") is not None:
                    return code, data["price"]
            except McdError:
                pass
            return code, None

        with cf.ThreadPoolExecutor(max_workers=workers) as ex:
            for code, price in ex.map(fetch, list(self.products.keys())):
                if price is not None:
                    self.products[code]["price"] = price
        return self

    def load_nutrition(self):
        raw = self.client.call("list-nutrition-foods", {})
        from nutrition_index import NutritionIndex
        self.nutrition = NutritionIndex(raw)
        return self

    def price_of(self, product_code, round_list=None, quantity=1):
        """官方核价。返回分（int）。round_list 里的 round 必须用 id。

        两种必须显式失败、绝不静默返回 0 的情况：
        1. 商品不可售 —— 服务端 success=true 但 data={}
        2. 商品不能脱离套餐单点 —— 服务端返回 price=0 且 productList=[]。
           实测：可乐中杯(3050)、无糖可乐中杯(3071) 单独核价都是这个形态。
           它们并非"免费"，若当成 0 元会让"单点 vs 套餐"的比价得出错误结论。
        """
        item = {"productCode": product_code, "quantity": quantity}
        if round_list:
            item["roundList"] = round_list
        data = self.client.call("calculate-price", dict(
            self._base_args(), items=[item]))
        if not isinstance(data, dict) or "price" not in data:
            raise McdError(
                f"核价未返回 price 字段（商品 {product_code} 可能不可售或已售罄）")
        price = data.get("price")
        if price is None:
            raise McdError(f"核价返回 price=None（商品 {product_code}）")
        if price == 0 and not data.get("productList"):
            raise McdError(
                f"商品 {product_code} 无法脱离套餐单独点（核价返回空商品列表），"
                f"不是 0 元")
        return price

    # ---------- 组合求解 ----------

    def combo_products(self):
        """可自由换购（3 个 round 都有选项）的套餐商品。"""
        out = []
        for p in self.products.values():
            rounds = [r for r in p.get("rounds", []) if r.get("choices")]
            if len(rounds) >= 3:
                out.append(p)
        return out

    def build_round_list(self, product, picks):
        """按 round 顺序构造 roundList。

        picks: {round_id: 子项code}
        注意：round 字段必须用 round['id']，用名称会触发服务端 500。
        """
        rl = []
        for r in product.get("rounds", []):
            rid = r.get("id")
            if rid is None:
                continue
            code = picks.get(rid) or picks.get(str(rid))
            if not code:
                continue
            rl.append({
                "round": str(rid),
                "comboItemList": [{"code": code, "quantity": 1}],
            })
        return rl

    def enumerate_combos(self, product, limit=200000):
        """枚举一个套餐的所有可算营养的子项组合。

        返回 list of {
            picks: {round_id: {code,name,diff}},
            nutrition: {sodium,protein,kcal,...},
            complete: bool,        # 所有组件是否都有营养数据
            missing: [组件名...],
            est_price: 分           # 按差价估算，仅用于排序，最终以官方核价为准
        }
        """
        if self.nutrition is None:
            raise RuntimeError("先调用 load_nutrition()")
        rounds = [r for r in product.get("rounds", []) if r.get("choices")]
        if not rounds:
            return []

        per_round = []
        for r in rounds:
            opts = []
            for ch in r["choices"]:
                std, vals = self.nutrition.match(ch.get("name", ""))
                opts.append({
                    "code": ch.get("code"),
                    "name": ch.get("name", ""),
                    "diff": parse_diff_price(ch.get("diffPrice")),
                    "is_default": ch.get("isDefault") == 1,
                    "std": std, "nutrition": vals,
                })
            per_round.append({"round_id": r.get("id"), "name": r.get("name", ""), "opts": opts})

        total = 1
        for pr in per_round:
            total *= len(pr["opts"])
        if total > limit:
            return []

        results = []
        for combo in itertools.product(*[pr["opts"] for pr in per_round]):
            picks = {}
            missing = []
            sodium = protein = kcal = 0.0
            complete = True
            diff_sum = 0.0
            for pr, ch in zip(per_round, combo):
                picks[pr["round_id"]] = ch
                diff_sum += ch["diff"]
                if ch["nutrition"] is None:
                    complete = False
                    missing.append(ch["name"])
                else:
                    sodium += ch["nutrition"]["sodium"]
                    protein += ch["nutrition"]["protein"]
                    kcal += ch["nutrition"]["kcal"]
            base = product.get("price") or 0
            results.append({
                "picks": picks,
                "picks_by_name": {pr["name"]: ch["name"] for pr, ch in zip(per_round, combo)},
                "nutrition": {
                    "sodium": sodium, "protein": protein, "kcal": kcal,
                    "fat": sum((ch["nutrition"]["fat"] if ch["nutrition"] else 0) for ch in combo),
                    "carb": sum((ch["nutrition"]["carb"] if ch["nutrition"] else 0) for ch in combo),
                },
                "complete": complete,
                "missing": missing,
                "est_price": int(round(base + diff_sum * 100)),
            })
        return results

    def solve(self, sodium_budget=None, protein_min=None, price_max=None,
              verify_top=3, top_k=5):
        """求解：在约束下找钠含量最低（并列时蛋白最高、价格最低）的组合。

        sodium_budget: 钠预算 mg
        protein_min:   蛋白下限 g
        price_max:     价格上限（元）
        verify_top:    对前 N 名做官方核价校验
        返回 dict {solutions: [...], stats: {...}}
        """
        if self.nutrition is None:
            self.load_nutrition()
        pool = []
        for product in self.combo_products():
            for combo in self.enumerate_combos(product):
                if not combo["complete"]:
                    continue
                n = combo["nutrition"]
                if sodium_budget is not None and n["sodium"] > sodium_budget:
                    continue
                if protein_min is not None and n["protein"] < protein_min:
                    continue
                if price_max is not None and combo["est_price"] > price_max * 100:
                    continue
                pool.append((product, combo))

        pool.sort(key=lambda pc: (
            pc[1]["nutrition"]["sodium"],
            -pc[1]["nutrition"]["protein"],
            pc[1]["est_price"],
        ))

        solutions = []
        for product, combo in pool[: max(top_k, verify_top)]:
            picks = {rid: ch["code"] for rid, ch in combo["picks"].items()}
            rl = self.build_round_list(product, picks)
            official = None
            try:
                official = self.price_of(product["code"], rl)
            except McdError:
                official = None
            solutions.append({
                "product_code": product["code"],
                "product_name": product["name"],
                "categories": product["categories"],
                "items": combo["picks_by_name"],
                "nutrition": combo["nutrition"],
                "est_price_yuan": round(combo["est_price"] / 100, 2),
                "official_price_yuan": round(official / 100, 2) if official is not None else None,
                "sodium_pct_daily": round(
                    combo["nutrition"]["sodium"] / 2000 * 100, 1),
            })
            if len(solutions) >= top_k:
                break

        return {
            "solutions": solutions,
            "stats": {
                "candidates_evaluated": len(pool),
                "combos_products": len(self.combo_products()),
                "products_total": len(self.products),
            },
        }

    # ---------- 单品横评 ----------

    def single_items(self):
        """没有套餐结构的单品（含营养与核价），用于同价位带横评。"""
        rows = []
        for p in self.products.values():
            if p.get("rounds"):
                continue
            if p.get("price") is None or not p.get("name"):
                continue
            std, vals = (None, None)
            if self.nutrition:
                std, vals = self.nutrition.match(p["name"])
            rows.append({
                "code": p["code"], "name": p["name"],
                "categories": p["categories"], "tags": p["tags"],
                "price_yuan": round(p["price"] / 100, 2),
                "nutrition": vals, "nutrition_name": std,
                "known": vals is not None,
            })
        return rows


def find_store(client, city, keyword, be_type=1):
    """按位置搜索门店。searchType=2 才是按位置搜；=1 只查收藏餐厅。"""
    data = client.call("query-nearby-stores", {
        "beType": be_type, "searchType": 2,
        "city": city, "keyword": keyword,
    })
    return data if isinstance(data, list) else data.get("list", [])


if __name__ == "__main__":
    import sys
    cli = McdClient()
    city = sys.argv[1] if len(sys.argv) > 1 else "上海"
    kw = sys.argv[2] if len(sys.argv) > 2 else "人民广场"
    stores = find_store(cli, city, kw)
    print(f"找到 {len(stores)} 家门店：")
    for s in stores[:5]:
        print(f"  {s.get('storeCode')} {s.get('storeName')} {s.get('distance')}m")
