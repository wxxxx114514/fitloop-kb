# -*- coding: utf-8 -*-
"""评测：判分靠字符串命中答案，不靠 LLM judge。
Recall@5 = top5 里包含期望答案的题数 / 总题数（排除应拒答的题）。"""
import sys, os, re, json
sys.path.insert(0, r"D:\project\fitloop-kb")
sys.stdout.reconfigure(encoding="utf-8")
import numpy as np
from kb.retrieve import BM25, load
from kb.query import expand

ROOT = r"D:\project\fitloop-kb"

def norm(t):
    t = re.sub(r"[～〜~—–\-]", "~", t)
    return re.sub(r"\s+", "", t)

# 期望答案（字面），来自指南正文；查不到就应当是拒答题
ANSWERS = {
    "成年人每天应该吃多少蔬菜": "300~500g",
    "每天吃盐不超过多少": "5g",
    "每天烹调油吃多少": "25~30g",
    "每天应该吃多少种食物": "12种以上",
    "全谷物和杂豆每天吃多少": "50~150g",
    "每天应该喝多少水": "1500~1700ml",
    "每天奶类摄入多少": "300~500g",
    "每天大豆及坚果吃多少": "25~35g",
    "成年人每周应该运动多少分钟": "150~300",
    "维生素D每天补多少国际单位": None,
}

def vec_scores(rows, qs):
    """一次性建索引，返回 {q: [(score, idx)]}"""
    from kb.embed import encode
    V = encode([r["text"] for r in rows])
    out = {}
    for q in qs:
        qv = encode([q])[0]
        cos = V @ qv
        out[q] = sorted(enumerate(cos), key=lambda x: -x[1])[:5]
    return out


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "bm25"
    rows = load()
    bm = BM25(rows)
    gold = [json.loads(l) for l in open(os.path.join(ROOT, "eval", "gold_10.jsonl"), encoding="utf-8")]
    hits, total, refuse_ok = 0, 0, 0
    vmap = vec_scores(rows, [g["q"] for g in gold]) if mode == "vector" else None
    use_expand = "expand" in sys.argv
    for g in gold:
        ans = ANSWERS.get(g["q"])
        # 统一成 (idx, score)
        qq = expand(g["q"]) if use_expand else g["q"]
        top = ([(i, sc) for i, sc in vmap[g["q"]]] if vmap
               else [(i, sc) for sc, i in bm.score(qq)[:5]])
        texts = [norm(rows[i]["text"]) for i, _ in top]
        if ans is None:
            ok = not top or all(sc < 3.0 for _, sc in top)   # 该拒：无命中
            refuse_ok += 1 if ok else 0
            print(f"{'OK ' if ok else 'MISS'} [应拒答] {g['q']}")
            continue
        total += 1
        ok = any(norm(ans) in t for t in texts)
        hits += 1 if ok else 0
        top_pages = [rows[i]["page"] for i, _ in top]
        print(f"{'OK ' if ok else 'MISS'} {g['q']:<22} 期望「{ans}」 top5 页 {top_pages}")
    print(f"\n{mode.upper()} Recall@5 = {hits}/{total} = {hits/max(1,total):.2f}")
    print(f"拒答正确 {refuse_ok}/1")

if __name__ == "__main__":
    main()