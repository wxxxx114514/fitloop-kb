# -*- coding: utf-8 -*-
"""两阶段：BM25(扩展) top-50 → Cross-Encoder 重排 → top5。字符串判分。"""
import sys, re, time
sys.path.insert(0, r"D:\project\fitloop-kb")
sys.stdout.reconfigure(encoding="utf-8")
from kb.retrieve import BM25, load
from kb.query import expand
from kb.rerank import Reranker

rows = load(); bm = BM25(rows); rr = Reranker()
def norm(t): return re.sub(r"\s+", "", re.sub(r"[～〜~—–\-]", "~", t))

ANS = {
    "成年人每天应该吃多少蔬菜": "300~500g", "每天吃盐不超过多少": "5g",
    "每天烹调油吃多少": "25~30g", "每天应该吃多少种食物": "12种以上",
    "全谷物和杂豆每天吃多少": "50~150g", "每天应该喝多少水": "1500~1700ml",
    "每天奶类摄入多少": "300~500g", "每天大豆及坚果吃多少": "25~35g",
    "成年人每周应该运动多少分钟": "150~300",
}

hits_b = hits_r = 0
t0 = time.time()
for q, a in ANS.items():
    qq = expand(q)
    cand = [i for _, i in bm.score(qq)[:50]]
    scores = rr.scores(qq, [rows[i]["text"] for i in cand])
    order = sorted(range(len(cand)), key=lambda k: -scores[k])
    before = [k for k, i in enumerate(cand, 1) if norm(a) in norm(rows[i]["text"])]
    after = [k for k, i in enumerate([cand[j] for j in order], 1) if norm(a) in norm(rows[i]["text"])] if False else \
            [k for k, j in enumerate(order, 1) if norm(a) in norm(rows[cand[j]]["text"])]
    ok_b = bool(before and before[0] <= 5)
    ok_r = bool(after and after[0] <= 5)
    hits_b += ok_b; hits_r += ok_r
    print(f"{q[:18]:<20} 前 {before[0] if before else '-':>4} → 后 {after[0] if after else '-':>4}   {'✓' if ok_r else '✗'}")

print(f"\nBM25@5        = {hits_b}/9")
print(f"BM25+Rerank@5 = {hits_r}/9   ({time.time()-t0:.0f}s)")
