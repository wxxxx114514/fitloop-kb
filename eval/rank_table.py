# -*- coding: utf-8 -*-
"""排名迁移表：每题答案块在 BM25 里的排名（不只看 top5）。"""
import sys, re, json
sys.path.insert(0, r"D:\project\fitloop-kb")
sys.stdout.reconfigure(encoding="utf-8")
from kb.retrieve import BM25, load
from kb.query import expand

rows = load(); bm = BM25(rows)
def norm(t): return re.sub(r"\s+", "", re.sub(r"[～〜~—–\-]", "~", t))

ANS = {
    "成年人每天应该吃多少蔬菜": "300~500g", "每天吃盐不超过多少": "5g",
    "每天烹调油吃多少": "25~30g", "每天应该吃多少种食物": "12种以上",
    "全谷物和杂豆每天吃多少": "50~150g", "每天应该喝多少水": "1500~1700ml",
    "每天奶类摄入多少": "300~500g", "每天大豆及坚果吃多少": "25~35g",
    "成年人每周应该运动多少分钟": "150~300",
}
print(f"{'题':<20}{'裸BM25':>8}{'加扩展':>8}")
for q, a in ANS.items():
    out = []
    for qq in (q, expand(q)):
        ranked = [i for _, i in bm.score(qq)]
        pos = [k for k, i in enumerate(ranked, 1) if norm(a) in norm(rows[i]["text"])]
        out.append(pos[0] if pos else 999)
    print(f"{q[:18]:<20}{out[0]:>8}{out[1]:>8}")
