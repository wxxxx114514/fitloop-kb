# -*- coding: utf-8 -*-
"""30 题判分器验证：直接喂真实块 → 看判分对错（不经检索）。
A: 同一数字不同主体  B: 多数字邻近（跑 window 30/60/90） C: 否定/限制语气"""
import sys, re, json
sys.path.insert(0, r"D:\project\fitloop-kb")
sys.path.insert(0, r"D:\project\fitloop-kb\eval")
sys.stdout.reconfigure(encoding="utf-8")
from kb.retrieve import load
from score import new_hit, load_gold

rows = load()
gold = {g["q"]: g for g in load_gold()}
def find(page, marker, prefer_table=False):
    hits = [r for r in rows if r["page"] == page and marker in re.sub(r"\s+", "", r["text"])]
    if not hits:
        return None
    if prefer_table:
        tbl = [r for r in hits if r["kind"] == "table"]
        if tbl:
            return re.sub(r"\s+", "", tbl[0]["text"])
    return re.sub(r"\s+", "", hits[0]["text"])

# (类别, 题, 页, 标记, 期望)
CASES = [
    ("A", "每天奶类摄入多少", 11,  "烟熏和腌制肉类", False),
    ("A", "每天奶类摄入多少", 72,  "奶制品",         True),
    ("A", "每天奶类摄入多少", 90,  "相当于每周吃鱼", False),
    ("A", "每天奶类摄入多少", 91,  "鱼、禽、蛋类",    False),
    ("A", "成年人每天应该吃多少蔬菜", 11, "烟熏和腌制肉类", False),
    ("A", "成年人每天应该吃多少蔬菜", 72, "不少于300g",    True),
    ("A", "每天应该喝多少水", 11,  "烟熏和腌制肉类", False),
    ("A", "每天应该喝多少水", 138, "适宜摄入量",     True),
    ("A", "每天奶类摄入多少", 70,  "液态奶",         True),
    ("A", "每天奶类摄入多少", 138, "适宜摄入量",     False),

    ("B", "每天吃盐不超过多少", 11, "食盐不超过", True),
    ("B", "每天烹调油吃多少", 11, "烹调油25",     True),
    ("B", "每天大豆及坚果吃多少", 72, "大豆制品",   True),
    ("B", "全谷物和杂豆每天吃多少", 72, "全谷物",   True),   # 选表格块
    ("B", "每天应该吃多少种食物", 72, "蔬菜|水果",  False),
    ("B", "每天大豆及坚果吃多少", 11, "烟熏和腌制肉类", False),
    ("B", "每天烹调油吃多少", 63, "蔬菜",         False),
    ("B", "每天吃盐不超过多少", 109, "少盐少油",   True),
    ("B", "全谷物和杂豆每天吃多少", 63, "全谷物",   True),    # 原文写「全谷物及杂豆50~150g」
    ("B", "每天应该吃多少种食物", 10, "12种以上",  True),

    ("C", "每天吃盐不超过多少", 11,  "食盐不超过",   True),
    ("C", "每天吃盐不超过多少", 109, "少盐少油",     True),
    ("C", "每天烹调油吃多少", 109, "烹调油摄入量", True),
    ("C", "全谷物和杂豆每天吃多少", 61, "少吃1~2口", False),
    ("C", "每天奶类摄入多少", 29, "避免营养缺乏",   False),
    ("C", "每天大豆及坚果吃多少", 46, "食不过量",    False),
    ("C", "每天应该喝多少水", 148, "增加饮水量",     False),   # 无具体数值，不算答对
    ("C", "成年人每周应该运动多少分钟", 43, "运动",   True),    # 原文「每周至少5天…累计150分钟以上」
    ("C", "每天烹调油吃多少", 11, "避免过多动物性油脂", True),
    ("C", "每天吃盐不超过多少", 46, "食不过量",      False),
]

def run(window_override=None):
    res = {}
    detail = []
    for cat, q, page, marker, expect in CASES:
        text = find(page, marker, prefer_table=(expect is True and "全谷物" in q))
        if text is None:
            detail.append((cat, q[:12], page, "块未找到", expect, None)); continue
        g = dict(gold[q])
        if window_override: g["window"] = window_override
        got = new_hit(text, g)
        res.setdefault(cat, [0, 0])
        res[cat][0] += 1; res[cat][1] += (got == expect)
        detail.append((cat, q[:12], page, "对" if got == expect else "错", expect, got))
    return res, detail

res, detail = run()
print("按类别：")
tot = 0; cor = 0
for cat in ("A", "B", "C"):
    n, ok = res[cat]; tot += n; cor += ok
    print(f"  {cat}: {ok}/{n} 正确  假阳/假阴 {n-ok} 例")
print(f"  合计 {cor}/{tot} = {cor/tot:.0%}\n")

print("错例:")
for cat, q, page, verdict, expect, got in detail:
    if verdict != "对":
        print(f"  [{cat}] p{page} {q} 期望{expect} 得到{got}")

print("\nwindow 敏感性（B 类 10 题）:")
for w in (30, 60, 90):
    r2, _ = run(w)
    print(f"  window={w:<3} A {r2['A'][1]}/10  B {r2['B'][1]}/10  C {r2['C'][1]}/10")