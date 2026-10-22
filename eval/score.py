# -*- coding: utf-8 -*-
"""两段式判分器：主体锚定 + 数值邻近性。保留旧的字面串判分做对照。

为什么需要它：300~500g 在鱼、奶、蔬菜里都出现，字面一样语义不同。
旧判分把"数字在块里"当成"答对了"，会误判。"""
import re, json, sys, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def _norm(t):
    t = re.sub(r"[～〜~—–\-]", "~", t)
    return re.sub(r"\s+", "", t)

def old_hit(text, answer):
    return _norm(answer) in _norm(text)

# 竞争主体：出现这些词，说明附近聊的不是本题的主体
FOODS = ["蔬菜", "水果", "鱼", "畜禽", "蛋类", "奶类", "奶制品", "大豆", "坚果",
         "全谷物", "杂豆", "食盐", "烹调油", "糖", "肉类"]

def _table_rows(text):
    """把清洗过的表格块还原成二维表：行用。分隔，格用 | 分隔。"""
    rows = []
    for line in re.split(r"[。]", text):
        cells = [c.strip() for c in line.split("|") if c.strip()]
        if len(cells) >= 2:
            rows.append(cells)
    return rows

def table_hit(text, g):
    """表格块按列对齐判分：主体词在表头列 → 取该列的值比对。"""
    rows = _table_rows(text)
    if len(rows) < 2:
        return None
    for ri, row in enumerate(rows):
        for ci, cell in enumerate(row):
            if any(_norm(s_) in _norm(cell) for s_ in g["subject"]):
                for r2 in rows[ri + 1:]:
                    if ci < len(r2) and any(_norm(v) in _norm(r2[ci]) for v in g["value"]):
                        return True
                # 表头命中但该列没值 → 明确判否，而不是回退到字符匹配
                if ri == 0:
                    return False
    return None

def new_hit(text, g, use_table=True):
    """两段式判分。
    表格块：主体在表头列 → 该列取值（字符距离不适用）。
    正文块：主体词锚定 + 数值在 window 内 + 中间不许夹别的主体词。"""
    if use_table:
        th = table_hit(text, g)
        if th is not None:
            return th
    t = _norm(text)
    others = [w for w in FOODS if not any(w in s for s in g["subject"])]
    for s in g["subject"]:
        for m in re.finditer(re.escape(_norm(s)), t):
            lo = max(0, m.start() - g["window"])
            hi = min(len(t), m.end() + g["window"])
            for v in g["value"]:
                pos = t.find(_norm(v), lo, hi)
                if pos < 0:
                    continue
                a, b = sorted((m.start(), pos))
                between = t[a:b]
                if any(o in between for o in others):
                    continue          # 中间夹着别的主体 → 不是这道题的答案
                # 警示语气：「不建议超过 X」不是推荐值
                pre = t[max(0, pos - 12):pos]
                if any(w in pre for w in ("不建议", "避免", "不要", "禁止", "不宜")):
                    continue
                return True
    return False

def load_gold(path=None):
    return json.load(open(path or os.path.join(ROOT, "eval", "gold_9.json"), encoding="utf-8"))

if __name__ == "__main__":
    g = load_gold()
    cases = [
        ("奶类每天摄入300ml液态奶即可", g[6], True),
        ("每周吃鱼2次或300~500g，蛋类300~350g", g[6], False),
        ("蔬菜每天不少于300g，水果200~350g", g[0], True),
        ("每天水的适宜摄入量为1700ml", g[5], True),
    ]
    print("单元测试:")
    for text, gg, expect in cases:
        got = new_hit(text, gg)
        print(f"  {'OK ' if got == expect else 'FAIL'} 期望{expect} 得到{got}  | {text[:34]} ← {gg['q'][:10]}")