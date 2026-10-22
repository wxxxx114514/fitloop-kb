# -*- coding: utf-8 -*-
"""对抗样例：人工构造陷阱，专门压 window 和表格列对齐。
这些文本不是从语料里挑的，是为"测边界"造的。"""
import sys
sys.path.insert(0, r"D:\project\fitloop-kb")
sys.path.insert(0, r"D:\project\fitloop-kb\eval")
sys.stdout.reconfigure(encoding="utf-8")
from score import new_hit, load_gold

gold = {g["q"]: g for g in load_gold()}

# (类别, 题, 构造文本, 期望)
CASES = [
    # A 同值不同主体：两样东西共用 300~500g
    ("A", "成年人每天应该吃多少蔬菜", "每周吃鱼2次或300~500g，畜禽肉300~500g，蛋类300~350g", False),
    ("A", "成年人每天应该吃多少蔬菜", "蔬菜300~500g，水果200~350g", True),
    ("A", "每天奶类摄入多少", "蔬菜300~500g，奶制品300~500g", True),
    ("A", "每天奶类摄入多少", "奶制品300~500g，鱼禽300~500g", True),
    ("A", "每天奶类摄入多少", "鱼300~500g，畜禽肉300~500g，蛋类300~350g", False),

    # B 否定/上限语气
    ("B", "成年人每天应该吃多少蔬菜", "不建议每天蔬菜超过500g", False),
    ("B", "每天吃盐不超过多少", "每天食盐不超过5g", True),
    ("B", "成年人每天应该吃多少蔬菜", "应避免摄入超过300g的蔬菜", False),
    ("B", "每天烹调油吃多少", "每天烹调油25~30g，避免过多", True),
    ("B", "每天奶类摄入多少", "不建议奶类超过300ml", False),

    # C 表格跨行：表头一行、值一行，中间隔着别的食物
    ("C", "全谷物和杂豆每天吃多少", "蔬菜|水果|全谷物|奶制品。每天|每天|每天|每天。不少于300g|200~350g|50~150g|300~500g", True),
    ("C", "每天奶类摄入多少", "蔬菜|水果|全谷物|奶制品。每天|每天|每天|每天。不少于300g|200~350g|50~150g|300~500g", True),
    ("C", "成年人每天应该吃多少蔬菜", "蔬菜|水果|全谷物|奶制品。每天|每天|每天|每天。200~350g|50~150g|300~500g|105~175g", False),
    ("C", "每天大豆及坚果吃多少", "蔬菜|水果|大豆制品|坚果。每天|每天|每天|每周。不少于300g|200~350g|105~175g|50~70g", True),
    ("C", "每天应该喝多少水", "蔬菜|水果|奶制品。每天|每天|每天。不少于300g|200~350g|300~500g", False),

    # D 距离边界：错值在 30 字内、对值在 60 字外 —— 专门压 window
    ("D", "每天奶类摄入多少", "奶类" + "的" * 45 + "300ml", True),
    ("D", "每天奶类摄入多少", "奶类" + "的" * 10 + "蔬菜300~500g" + "的" * 40 + "300ml", False),
    ("D", "成年人每天应该吃多少蔬菜", "蔬菜" + "的" * 80 + "300g", True),
]

def run(window=None):
    res, bad = {}, []
    for cat, q, text, expect in CASES:
        g = dict(gold[q])
        if window: g["window"] = window
        got = new_hit(text, g)
        res.setdefault(cat, [0, 0]); res[cat][0] += 1; res[cat][1] += (got == expect)
        if got != expect:
            bad.append((cat, q, text, expect, got))
    return res, bad

res, bad = run()
tot = sum(v[0] for v in res.values()); ok = sum(v[1] for v in res.values())
print(f"对抗样例：{ok}/{tot}\n")
for cat in "ABCD":
    if cat in res: print(f"  {cat}: {res[cat][1]}/{res[cat][0]}")
print()
for cat, q, text, expect, got in bad:
    print(f"[{cat}] {q}  期望{expect} 得到{got}")
    print(f"   {text[:80]}")
print("\nwindow 敏感性:")
for w in (30, 60, 90):
    r2, b2 = run(w)
    t2 = sum(v[0] for v in r2.values()); o2 = sum(v[1] for v in r2.values())
    print(f"  window={w:<3} {o2}/{t2}   A {r2['A'][1]}/5  B {r2['B'][1]}/5  C {r2['C'][1]}/5  D {r2.get('D',[0,0])[1]}/3")