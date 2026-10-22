# -*- coding: utf-8 -*-
"""规则重排：营养指南的答案几乎都"带数字单位"，且必然含题干的核心名词。
不依赖任何模型，纯启发式。"""
import sys, re
sys.path.insert(0, r"D:\project\fitloop-kb")
sys.stdout.reconfigure(encoding="utf-8")
from kb.retrieve import BM25, load, tokens
from kb.query import expand

rows = load(); bm = BM25(rows)
def norm(t): return re.sub(r"\s+", "", re.sub(r"[～〜~—–\-]", "~", t))

NUM_UNIT = re.compile(r"\d+\s*[~\-]?\s*\d*\s*(g|ml|克|毫升|kcal|千卡|分钟|小时)", re.I)
STOP = set("每天应该多少什么怎么可以需不需要吃喝".replace(" ", ""))

ANS = {
    "成年人每天应该吃多少蔬菜": "300~500g", "每天吃盐不超过多少": "5g",
    "每天烹调油吃多少": "25~30g", "每天应该吃多少种食物": "12种以上",
    "全谷物和杂豆每天吃多少": "50~150g", "每天应该喝多少水": "1500~1700ml",
    "每天奶类摄入多少": "300~500g", "每天大豆及坚果吃多少": "25~35g",
    "成年人每周应该运动多少分钟": "150~300",
}

def core_words(q):
    """题干里的实词（2-gram，去掉停用字组成的）"""
    ws = set(tokens(q))
    return {w for w in ws if not (set(w) <= STOP)}

hit_b = hit_r = 0
print(f"{'题':<20}{'BM25':>6}{'规则重排':>8}  重排前排/后")
for q, a in ANS.items():
    qq = expand(q)
    cand = [(s, i) for s, i in bm.score(qq)[:50]]
    cw = core_words(q)
    def boost(s, i):
        t = rows[i]["text"]
        b = 1.0
        if NUM_UNIT.search(t): b += 0.8
        if any(w in t for w in cw): b += 0.5
        if rows[i].get("kind") == "table": b += 0.2
        return s * b
    rer = sorted(((boost(s, i), i) for s, i in cand), reverse=True)
    ok_b = any(norm(a) in norm(rows[i]["text"]) for _, i in cand[:5])
    ok_r = any(norm(a) in norm(rows[i]["text"]) for _, i in rer[:5])
    hit_b += ok_b; hit_r += ok_r
    rb = [k for k, (_, i) in enumerate(cand, 1) if norm(a) in norm(rows[i]["text"])]
    rr = [k for k, (_, i) in enumerate(rer, 1) if norm(a) in norm(rows[i]["text"])]
    print(f"{q[:18]:<20}{'✓' if ok_b else '✗':>6}{'✓' if ok_r else '✗':>8}  {rb[0] if rb else '-'}/{rr[0] if rr else '-'}")
print(f"\nBM25     = {hit_b}/9")
print(f"规则重排  = {hit_r}/9")
