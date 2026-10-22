# -*- coding: utf-8 -*-
"""网格搜 k1 × b，用同一套 9 题定 Recall@5。直接仲裁"降 b 还是升 b"。"""
import sys, os, re, json
sys.path.insert(0, r"D:\project\fitloop-kb")
sys.stdout.reconfigure(encoding="utf-8")
from kb.retrieve import BM25, load

ROOT = r"D:\project\fitloop-kb"
ANSWERS = {
    "成年人每天应该吃多少蔬菜": "300~500g", "每天吃盐不超过多少": "5g",
    "每天烹调油吃多少": "25~30g", "每天应该吃多少种食物": "12种以上",
    "全谷物和杂豆每天吃多少": "50~150g", "每天应该喝多少水": "1500~1700ml",
    "每天奶类摄入多少": "300~500g", "每天大豆及坚果吃多少": "25~35g",
    "成年人每周应该运动多少分钟": "150~300",
}
def norm(t): return re.sub(r"\s+", "", re.sub(r"[～〜~—–\-]", "~", t))

rows = load()
gold = [json.loads(l) for l in open(os.path.join(ROOT, "eval", "gold_10.jsonl"), encoding="utf-8")]
qs = [g["q"] for g in gold if g["q"] in ANSWERS]

print(f"{'k1':<6}{'b':<6}Recall@5")
print("-" * 24)
best = None
for k1 in (1.0, 1.2, 1.5, 2.0):
    for b in (0.3, 0.5, 0.75, 0.9):
        bm = BM25(rows, k1=k1, b=b)
        hit = 0
        for q in qs:
            top = [i for _, i in bm.score(q)[:5]]
            if any(norm(ANSWERS[q]) in norm(rows[i]["text"]) for i in top):
                hit += 1
        mark = ""
        if best is None or hit > best[0]:
            best = (hit, k1, b); mark = "  ←"
        print(f"{k1:<6}{b:<6}{hit}/9{mark}")
print(f"\n最好: k1={best[1]}, b={best[2]}, Recall={best[0]}/9")
