"""营养库索引：解析 list-nutrition-foods 返回，并把在售商品名对齐到营养条目。

麦当劳 MCP 的营养库是一个扁平文本表：

    [160]{productName,nutritionDescription,energyKj,energyKcal,protein,fat,
          carbohydrate,sodium,calcium}:
      猪柳麦满分,null,1288,308,16,16,24,781,213

对齐难点：营养库按"标准款"命名，门店在售商品可能带规格前缀、套餐后缀、
品牌前缀、括号补充说明，甚至门店新品根本没进营养库。匹配不到时必须
诚实返回 None —— 宁可说"数据缺失"，也不能用邻近条目凑数。
"""

import re
import unicodedata

FIELDS = ("kj", "kcal", "protein", "fat", "carb", "sodium", "calcium")

# 单人每日钠参考摄入量上限（《中国居民膳食指南》推荐 <2000mg）
DAILY_SODIUM_LIMIT_MG = 2000


def parse_nutrition(raw):
    """解析 MCP list-nutrition-foods 的 data 字符串为 {名称: 营养字典}。"""
    if not raw:
        return {}
    if isinstance(raw, dict):
        raw = raw.get("data") or ""
    body = str(raw).split("}:", 1)[-1]
    out = {}
    for line in body.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        parts = [x.strip() for x in line.split(",")]
        if len(parts) < 9:
            continue
        try:
            vals = [float(x) for x in parts[2:9]]
        except ValueError:
            continue
        out[parts[0]] = dict(zip(FIELDS, vals))
    return out


_BRACKET = re.compile(r"[（(][^)）]*[)）]")
_PUNCT = re.compile(r"[™®\s\-—·、,，。\"“”'’!！?？:：/＋+]")


def normalize(name):
    """归一化商品名：去括号补充说明、去标点、NFKC 统一全半角。"""
    if not name:
        return ""
    s = unicodedata.normalize("NFKC", str(name))
    s = _BRACKET.sub("", s)
    s = _PUNCT.sub("", s)
    return s


def variants(name):
    """生成一个商品名的候选匹配形式，按优先级排列。"""
    base = normalize(name)
    if not base:
        return []
    cands = [base]
    # "5块心形薯饼+韩式辣椒黄油风味酱" → 主体 "5块心形薯饼"
    if "+" in base:
        cands.append(base.split("+")[0])
    # "麦咖啡冰美式中杯" → "冰美式中杯"
    if base.startswith("麦咖啡"):
        cands.append(base[3:])
    # 规格前缀：大/中/小/迷你/加大 → 同时保留去规格名
    m = re.match(r"^(大|中|小|迷你|加大)(.+)$", base)
    if m:
        cands.append(m.group(2))
    # 数量前缀："5块麦乐鸡" → "麦乐鸡"
    m = re.match(r"^\d+块(.+)$", base)
    if m:
        cands.append(m.group(1))
    return [c for c in dict.fromkeys(cands) if c]


class NutritionIndex:
    """营养库查询索引。"""

    def __init__(self, raw=None, items=None):
        self.items = items if items is not None else parse_nutrition(raw)
        self._exact = {}
        for name, vals in self.items.items():
            self._exact.setdefault(normalize(name), (name, vals))
        # 前缀索引只收长度 >= 3 的名字，避免"中薯"这类误配
        self._prefix = {}
        for name, vals in self.items.items():
            n = normalize(name)
            if len(n) >= 3:
                self._prefix.setdefault(n, (name, vals))

    def match(self, name):
        """对齐单个商品名。返回 (标准名, 营养字典)；对不上返回 (None, None)。"""
        if not name:
            return (None, None)
        for cand in variants(name):
            if cand in self._exact:
                return self._exact[cand]
        for cand in variants(name):
            if len(cand) < 3:
                continue
            for norm_name, (std, vals) in self._prefix.items():
                if abs(len(norm_name) - len(cand)) <= 3 and (
                    norm_name.startswith(cand) or cand.startswith(norm_name)
                ):
                    return (std, vals)
        return (None, None)

    def coverage(self, names):
        """返回 (命中数, 总数)。"""
        hit = sum(1 for n in names if self.match(n)[0])
        return hit, len(names)

    def sodium_rank(self, names):
        """把一批商品名按钠含量升序排，未匹配的排到最后（并标注缺失）。"""
        rows = []
        for n in names:
            std, vals = self.match(n)
            if std:
                rows.append({"name": n, "std": std, "sodium": vals["sodium"],
                             "protein": vals["protein"], "kcal": vals["kcal"], "known": True})
            else:
                rows.append({"name": n, "std": None, "sodium": None,
                             "protein": None, "kcal": None, "known": False})
        return sorted(rows, key=lambda r: (not r["known"], r["sodium"] if r["sodium"] is not None else 0))


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else None
    raw = open(path, encoding="utf-8").read() if path else ""
    idx = NutritionIndex(raw)
    print(f"解析营养条目：{len(idx.items)}")
    for probe in sys.argv[2:]:
        std, vals = idx.match(probe)
        print(f"  {probe} → {std or '未匹配'}", vals or "")
