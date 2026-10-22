# -*- coding: utf-8 -*-
"""三档对比：BM25 / 向量 / RRF 融合。向量算一次存盘复用。"""
import sys, os, re, json
sys.path.insert(0, r"D:\project\fitloop-kb")
sys.stdout.reconfigure(encoding="utf-8")
import numpy as np
from kb.retrieve import BM25, load

ROOT = r"D:\project\fitloop-kb"
CACHE = os.path.join(ROOT, "corpus", "emb_375.npy")

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


def norm(t):
    return re.sub(r"\s+", "", re.sub(r"[～〜~—–\-]", "~", t))


def main():
    rows = load()
    bm = BM25(rows)
    gold = [json.loads(l) for l in open(os.path.join(ROOT, "eval", "gold_10.jsonl"), encoding="utf-8")]
    qs = [g["q"] for g in gold]

    if os.path.exists(CACHE):
        V = np.load(CACHE)
    else:
        from kb.embed import encode
        V = encode([r["text"] for r in rows])
        np.save(CACHE, V)
    QV = None
    from kb.embed import encode as enc
    QV = enc(qs)

    def bm_top(q, k=20):
        return [i for _, i in bm.score(q)[:k]]

    def vec_top(qi, k=20):
        cos = V @ QV[qi]
        return [i for i in np.argsort(-cos)[:k]]

    def rrf(qi, k=60):
        a, b = bm_top(qs[qi]), vec_top(qi)
        sc = {}
        for lst in (a, b):
            for r, i in enumerate(lst):
                sc[i] = sc.get(i, 0) + 1.0 / (k + r + 1)
        return [i for i, _ in sorted(sc.items(), key=lambda x: -x[1])[:5]]

    res = {"bm25": 0, "vec": 0, "rrf": 0}
    for qi, g in enumerate(gold):
        ans = ANSWERS.get(g["q"])
        if ans is None:
            continue
        top_b = [i for _, i in bm.score(g["q"])[:5]]
        top_v = vec_top(qi, 5)
        top_r = rrf(qi)
        for name, top in (("bm25", top_b), ("vec", top_v), ("rrf", top_r)):
            if any(norm(ans) in norm(rows[i]["text"]) for i in top):
                res[name] += 1
    print("Recall@5：")
    for k, v in res.items():
        print(f"  {k:<5} {v}/9 = {v/9:.2f}")


if __name__ == "__main__":
    main()
