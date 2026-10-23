# -*- coding: utf-8 -*-
"""三档 × 两种问法：BM25+重排 / 结构化别名 / 结构化+改写+回落。"""
import sys, re, json, sqlite3
sys.path.insert(0, r"D:\project\fitloop-kb")
sys.path.insert(0, r"D:\project\fitloop-kb\eval")
sys.stdout.reconfigure(encoding="utf-8")
from kb.retrieve import BM25, load
from kb.query import expand
from kb.rerank import Reranker
from kb.rewrite import terms as rewrite
from score import new_hit

DB = r"D:\project\fitloop-kb\kb.db"
rows = load(); bm = BM25(rows); rr = Reranker()
byid = {r["id"]: r for r in rows}
gold = json.load(open(r"D:\project\fitloop-kb\eval\gold_9.json", encoding="utf-8"))
facts = sqlite3.connect(DB).execute(
    "SELECT chunk_id,page,subject,metric,value,unit,alias FROM facts").fetchall()

SPOKEN = {
    "成年人每天应该吃多少蔬菜": "一天得吃多少菜啊",
    "每天吃盐不超过多少": "盐一天别超多少",
    "每天烹调油吃多少": "炒菜放多少油合适",
    "每天应该吃多少种食物": "每天吃的种类要几种",
    "全谷物和杂豆每天吃多少": "粗粮杂豆吃多少",
    "每天应该喝多少水": "一天喝几杯水",
    "每天奶类摄入多少": "牛奶酸奶一天喝多少",
    "每天大豆及坚果吃多少": "坚果能抓一把吗",
    "成年人每周应该运动多少分钟": "一周得动弹多久",
}

def n(t): return re.sub(r"\s+", "", re.sub(r"[～〜~—–\-]", "~", str(t)))

def bm25_hit(q, g):
    qq = expand(q)
    cand = [i for _, i in bm.score(qq)[:30]]
    if not cand: return False
    sc = rr.scores(qq, [rows[i]["text"] for i in cand])
    top = [cand[k] for k in sorted(range(len(cand)), key=lambda k: -sc[k])][:5]
    return any(new_hit(rows[i]["text"], g) for i in top)

def fact_ok(f, g):
    subj = n(f[2]); val = n(f[4]) + n(f[5] or "")
    if not any(n(s) in subj for s in g["subject"]): return False
    return any(n(v) in val or val in n(v) for v in g["value"])

def match_facts(q, g):
    for f in facts:
        names = [f[2]] + (json.loads(f[6]) if f[6] else [])
        if any(x and x in q for x in names) and fact_ok(f, g):
            return f
    return None

def run(q, g, allow_rewrite):
    if bm25_hit(q, g): return "bm25"
    if match_facts(q, g): return "alias"
    if allow_rewrite:
        for t in rewrite(q):
            f = match_facts(t, g)
            if f: return "rewrite"
    return "miss"

print(f"{'题':<20}{'书面A':>7}{'书面B':>7}{'口语A':>7}{'口语B':>7}{'口语C':>7}")
score = {"wb_a":0,"wb_b":0,"sk_a":0,"sk_b":0,"sk_c":0}
for g in gold:
    qw, qs = g["q"], SPOKEN[g["q"]]
    wa = run(qw, g, False) != "miss"
    wb = run(qw, g, True) != "miss"
    sa = run(qs, g, False) != "miss"
    sb = match_facts(qs, g) is not None or sa
    sc = run(qs, g, True) != "miss"
    score["wb_a"] += wa; score["wb_b"] += wb
    score["sk_a"] += sa; score["sk_b"] += sb; score["sk_c"] += sc
    print(f"{qw[:18]:<20}{'✓' if wa else '✗':>7}{'✓' if wb else '✗':>7}{'✓' if sa else '✗':>7}{'✓' if sb else '✗':>7}{'✓' if sc else '✗':>7}")

print(f"\nA = BM25+重排    B = 结构化(别名+改写)")
print(f"书面  A {score['wb_a']}/9   B {score['wb_b']}/9")
print(f"口语  A {score['sk_a']}/9   B {score['sk_b']}/9   C(含改写) {score['sk_c']}/9")
print(f"\n事实库: {len(facts)} 条，覆盖 {len({f[2] for f in facts})} 个主体")