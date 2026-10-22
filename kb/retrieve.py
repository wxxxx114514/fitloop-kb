# -*- coding: utf-8 -*-
"""最简 BM25（中文按字符 bigram），先证明链路通，不追求效果。"""
import os, re, sys, sqlite3, math
sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "kb.db")


def tokens(s):
    s = re.sub(r"[^\u4e00-\u9fffA-Za-z0-9]", "", s).lower()
    return [s[i:i + 2] for i in range(len(s) - 1)] or [s]


class BM25:
    def __init__(self, rows, k1=1.5, b=0.75):
        self.rows = rows
        self.docs = [tokens(r["text"]) for r in rows]
        self.avg = sum(len(d) for d in self.docs) / max(1, len(self.docs))
        self.df = {}
        for d in self.docs:
            for t in set(d):
                self.df[t] = self.df.get(t, 0) + 1
        self.k1, self.b, self.N = k1, b, len(rows)
        # 小贴士框降权：样板文字查询词密度高但不含答案
        self.w = [0.5 if r.get("is_tip") else 1.0 for r in rows]

    def score(self, q):
        qt = tokens(q)
        out = []
        for i, d in enumerate(self.docs):
            dl = len(d)
            s = 0.0
            for t in qt:
                if t not in self.df:
                    continue
                f = d.count(t)
                if not f:
                    continue
                idf = math.log(1 + (self.N - self.df[t] + 0.5) / (self.df[t] + 0.5))
                s += idf * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * dl / self.avg))
            s *= self.w[i]
            if s > 0:
                out.append((s, i))
        out.sort(reverse=True)
        return out


def load():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    rows = con.execute("SELECT id, source, page, text, COALESCE(is_tip,0) AS is_tip, "
                       "COALESCE(kind,'text') AS kind FROM chunks").fetchall()
    con.close()
    return [dict(r) for r in rows]


def main():
    rows = load()
    bm = BM25(rows)
    qs = ["蛋白质每天吃多少", "蔬菜水果推荐量", "减脂 热量 控制"]
    for q in qs:
        hits = bm.score(q)[:3]
        print(f"\n问：{q}")
        if not hits:
            print("  （没有命中）")
        for s, i in hits:
            r = rows[i]
            print(f"  {s:5.2f}  {r['id']:<24} p{r['page']}  {r['text'][:60]}")


if __name__ == "__main__":
    main()