# -*- coding: utf-8 -*-
"""新旧判分器对照：BM25 / BM25+Rerank 各跑一遍，逐题标出差异。"""
import sys, re
sys.path.insert(0, r"D:\project\fitloop-kb")
sys.path.insert(0, r"D:\project\fitloop-kb\eval")
sys.stdout.reconfigure(encoding="utf-8")
from kb.retrieve import BM25, load
from kb.query import expand
from kb.rerank import Reranker
from score import new_hit, old_hit, load_gold

gold = load_gold()
rows = load(); bm = BM25(rows); rr = Reranker()

# 旧判分用的字面串（保持原样，好做对照）
OLD_ANSWERS = {
    "成年人每天应该吃多少蔬菜": "300~500g", "每天吃盐不超过多少": "5g",
    "每天烹调油吃多少": "25~30g", "每天应该吃多少种食物": "12种以上",
    "全谷物和杂豆每天吃多少": "50~150g", "每天应该喝多少水": "1500~1700ml",
    "每天奶类摄入多少": "300~500g", "每天大豆及坚果吃多少": "25~35g",
    "成年人每周应该运动多少分钟": "150~300",
}

res = {"bm25_old": 0, "bm25_new": 0, "rr_old": 0, "rr_new": 0}
print(f"{'题':<20}{'BM25旧':>7}{'BM25新':>7}{'重排旧':>7}{'重排新':>7}  差异")
for g in gold:
    q = g["q"]
    qq = expand(q)
    cand = [i for _, i in bm.score(qq)[:50]]
    top_b = cand[:5]
    sc = rr.scores(qq, [rows[i]["text"] for i in cand])
    top_r = [cand[k] for k in sorted(range(len(cand)), key=lambda k: -sc[k])][:5]

    o = OLD_ANSWERS[q]
    bo = any(old_hit(rows[i]["text"], o) for i in top_b)
    bn = any(new_hit(rows[i]["text"], g) for i in top_b)
    ro = any(old_hit(rows[i]["text"], o) for i in top_r)
    rn = any(new_hit(rows[i]["text"], g) for i in top_r)
    res["bm25_old"] += bo; res["bm25_new"] += bn
    res["rr_old"] += ro; res["rr_new"] += rn
    diff = "旧误判" if (rn and not ro) else ("新误判" if (ro and not rn) else "")
    print(f"{q[:18]:<20}{'✓' if bo else '✗':>7}{'✓' if bn else '✗':>7}{'✓' if ro else '✗':>7}{'✓' if rn else '✗':>7}  {diff}")

print(f"\n{'':<20}{res['bm25_old']:>6}{res['bm25_new']:>7}{res['rr_old']:>8}{res['rr_new']:>7}  /9")
