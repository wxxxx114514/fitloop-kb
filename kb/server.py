# -*- coding: utf-8 -*-
"""fitloop-kb 的 MCP server：四个工具。
约定：检索为空就返回空数组/空结果，让调用方拒答；每条结果必须带 source + page。"""
import os, sys, sqlite3, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp.server.mcpserver import MCPServer
from kb.retrieve import BM25, load
from kb.query import expand
from kb.sources import title_of

_RERANK = None

def _reranker():
    """重排器可选：模型文件不在就退回纯 BM25。"""
    global _RERANK
    if _RERANK is None:
        try:
            from kb.rerank import Reranker
            _RERANK = Reranker()
        except Exception:
            _RERANK = False
    return _RERANK or None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "kb.db")
MIN_SCORE = 3.0          # 低于这个就当作"语料里没有"，先拍的，后面用 gold 集标定

mcp = MCPServer("fitloop-kb")
_rows, _bm25 = None, None


def _idx():
    global _rows, _bm25
    if _bm25 is None:
        _rows = load()
        _bm25 = BM25(_rows)
    return _rows, _bm25


@mcp.tool()
def search_guideline(query: str, k: int = 5) -> dict:
    """按自然语言查指南原文。返回带 source/page 的片段；没有就返回空。"""
    rows, bm = _idx()
    q = expand(query)                      # 口语 → 指南用词
    cand = [(s, i) for s, i in bm.score(q)[:30] if s >= MIN_SCORE]
    rr = _reranker()
    if rr and cand:
        scores = rr.scores(q, [rows[i]["text"] for _, i in cand])
        order = sorted(range(len(cand)), key=lambda j: -scores[j])
        hits = [cand[j] for j in order][:k]
    else:
        hits = cand[:k]
    return {
        "results": [
            {"chunk_id": rows[i]["id"], "source": rows[i]["source"],
             "title": title_of(rows[i]["source"]),        # 人名可读的书名，由 kb 提供
             "page": rows[i]["page"], "text": rows[i]["text"], "score": round(s, 2)}
            for s, i in hits
        ],
        "note": None if hits else "语料里没有命中，调用方应拒答而不是让模型编",
    }


@mcp.tool()
def cite(chunk_id: str) -> dict:
    """按 chunk_id 取原文，防止模型改写引用。"""
    con = sqlite3.connect(DB)
    row = con.execute("SELECT id, source, page, text FROM chunks WHERE id=?", (chunk_id,)).fetchone()
    con.close()
    if not row:
        return {"error": "chunk_id 不存在"}
    return {"chunk_id": row[0], "source": row[1], "page": row[2], "text": row[3]}


@mcp.tool()
def lookup_food(name: str) -> dict:
    """按名称查营养值（走表，不走向量）。现在只有占位：英文查 USDA，查不到返回空。"""
    import urllib.parse, urllib.request
    UA = {"User-Agent": "fitloop-kb/0.1"}
    u = ("https://api.nal.usda.gov/fdc/v1/foods/search?query="
         + urllib.parse.quote(name) + "&pageSize=1&api_key=DEMO_KEY")
    try:
        d = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=20).read())
        foods = d.get("foods", [])
        if not foods:
            return {"query": name, "matched": None, "note": "查不到，别猜"}
        f = foods[0]
        nut = {}
        for n in f.get("foodNutrients", []):
            key = (n.get("nutrientName") or "").lower()
            if key in ("energy", "protein", "total lipid (fat)", "carbohydrate, by difference"):
                nut[key] = n.get("value")
        return {"query": name, "matched": f.get("description"), "per_100g": nut,
                "source": "usda-fdc", "fdc_id": f.get("fdcId")}
    except Exception as e:
        return {"query": name, "error": f"{type(e).__name__}: {str(e)[:60]}"}


@mcp.tool()
def get_recommendation(topic: str, population: str = "adult") -> dict:
    """精确数值查询。**只返回证据，不替调用方选**（decision_owner 永远是 caller）。"""
    rows, bm = _idx()
    hits = bm.score(topic)[:3]
    out = []
    for s, i in hits:
        if s < MIN_SCORE:
            continue
        out.append({"source": rows[i]["source"], "page": rows[i]["page"],
                    "quote": rows[i]["text"][:120], "score": round(s, 2)})
    return {"topic": topic, "population": population, "evidence": out,
            "decision_owner": "caller",
            "conflict": len({e["source"] for e in out}) > 1}


if __name__ == "__main__":
    mcp.run()