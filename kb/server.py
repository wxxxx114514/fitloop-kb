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

def _facts():
    """结构化事实表：由 build/extract_all.py 离线生成，值都经过原文校验。"""
    con = sqlite3.connect(DB)
    rows = con.execute("SELECT chunk_id, page, subject, value, unit, alias, "
                       "COALESCE(scope,'day'), per_day FROM facts").fetchall()
    con.close()
    out = []
    for cid, page, subj, val, unit, alias, scope, per_day in rows:
        try:
            al = json.loads(alias) if alias else []
        except Exception:
            al = []
        out.append({"chunk_id": cid, "page": page, "subject": subj, "value": val,
                    "unit": unit or "", "names": [subj] + al,
                    "scope": scope, "per_day": per_day})
    return out


# 出现这些词就不给证据，让调用方去走就医流程。
# kb 这条不能靠模型判断，必须是写死的词表 —— 判定不得外借。
SINGLE_OK = set("盐油水菜奶鱼蛋肉糖酒茶钙铁锌")   # 允许当作名字的单字

MEDICAL = ("疼", "痛", "受伤", "扭", "拉伤", "肿", "麻", "骨", "头晕", "发烧",
           "骨折", "手术", "药", "怀孕", "糖尿病", "高血压")

_VEC = None

def _vectors():
    """语料向量（离线算好存盘）。没有文件就返回 None，回落到纯 BM25。"""
    global _VEC
    if _VEC is None:
        try:
            import numpy as np
            p = os.path.join(ROOT, "corpus", "emb_609.npy")
            ids = os.path.join(ROOT, "corpus", "emb_609_ids.json")
            if os.path.exists(p) and os.path.exists(ids):
                _VEC = (np.load(p), json.load(open(ids, encoding="utf-8")))
            else:
                _VEC = False
        except Exception:
            _VEC = False
    return _VEC or None

_FACTS = None

def facts_match(query, limit=3):
    """第一层：主体/别名精确匹配。

    **返回多条，不替调用方选**——同一主体在书里可能有好几个指标
    （身体活动既有"6000步"也有"150~300分钟"），选哪个是调用方的事。
    """
    global _FACTS
    if _FACTS is None:
        try:
            _FACTS = _facts()
        except Exception:
            _FACTS = []
    q = query or ""
    scored, seen = [], set()
    for f in _FACTS:
        if not any(ch.isdigit() for ch in (f["value"] or "")):
            continue
        # 单字名只放行常见的食物/营养单字，避免「水」在「水果」里误命中
        name = max((n for n in f["names"] if n and ((len(n) >= 2) or (n in SINGLE_OK)) and n in q),
                   key=len, default=None)
        if not name:
            continue
        key = (f["subject"], f["value"], f["unit"])
        if key in seen:
            continue
        # 关键：还要看「问的是不是这个指标」——否则「身体活动」会把所有运动题都吃掉
        metric = f.get("metric") or ""
        m_hit = sum(1 for i in range(len(metric) - 1) if metric[i:i + 2] in q)
        # 问「一天」时优先每日量，问「一周」时优先每周量
        want_week = any(w in q for w in ("一周", "每周", "周吃", "周摄"))
        want_day = any(w in q for w in ("一天", "每天", "每日", "一天吃"))
        sc = f.get("scope") or "day"
        scope_bonus = 6 if ((want_week and sc == "week") or (want_day and sc == "day")) else 0
        if metric and m_hit == 0:
            score = len(name)                      # 指标完全对不上，只作低分候选
        else:
            score = 10 + len(name) + m_hit * 4 + scope_bonus
        seen.add(key)
        scored.append((score, f))
    scored.sort(key=lambda x: -x[0])
    return [f for s_, f in scored if s_ >= 10][:limit] or [f for _, f in scored][:limit]


VERIFY_SYS = """判断候选事实里，哪些对回答用户的问题**有帮助**。
只输出 JSON：{"keep":[编号]}；一条都没帮助就返回 {"keep":[]}。
规则：
- 部分回答也算（问"几点吃"，给出时间区间就保留）
- 同一个数字但答的是别的问题（问"隔夜水"，给的是"每天喝多少水"）→ 不保留
- 宁可保留一条，也不要因为不完美而全丢
"""

def verify(query, hits, timeout=8.0):
    """最后一道筛：让模型判断候选是否真的回答了问题。失败就原样返回，不放行也不误杀。"""
    if not hits:
        return hits
    try:
        from kb.rewrite import _key
        import httpx
        key, base = _key()
        if not key:
            return hits
        listing = "\n".join(f"{i+1}. {h['subject']}：{h['value']}{h['unit']}" for i, h in enumerate(hits))
        r = httpx.post(base.rstrip("/") + "/chat/completions",
                       headers={"Authorization": "Bearer " + key},
                       json={"model": "deepseek-chat", "temperature": 0,
                             "response_format": {"type": "json_object"},
                             "messages": [{"role": "system", "content": VERIFY_SYS},
                                          {"role": "user", "content": f"问题：{query}\n候选：\n{listing}"}]},
                       timeout=timeout)
        keep = json.loads(r.json()["choices"][0]["message"]["content"]).get("keep") or []
        kept = [hits[i - 1] for i in keep if isinstance(i, int) and 1 <= i <= len(hits)]
        return kept
    except Exception:
        return hits


mcp = MCPServer("fitloop-kb")
_rows, _bm25 = None, None


def _idx():
    global _rows, _bm25
    if _bm25 is None:
        _rows = load()
        _bm25 = BM25(_rows)
    return _rows, _bm25


def search(query, k=5, verify_on=True):
    """三层检索的唯一实现：别名 → 改写 → BM25+重排。工具和评测都走这里。"""
    if any(k in (query or "") for k in MEDICAL):
        return {"results": [],
                "note": "涉及身体不适或用药，知识库不作答，请调用方引导就医"}

    rows, bm = _idx()
    q = expand(query)                      # 口语 → 指南用词

    def show(h):
        """value 里已经带单位就不要再拼一次；每周量附每日当量。"""
        v, u = str(h["value"]), str(h["unit"] or "")
        txt = f"{v}" if (u and v.endswith(u)) else f"{v}{u}"
        extra = ""
        if h.get("scope") == "week":
            per = h.get("per_day")
            extra = f"（约 {per}/天）" if per else "（每周）"
        elif h.get("scope") == "month":
            per = h.get("per_day")
            extra = f"（约 {per}/天）" if per else "（每月）"
        return f"{h['subject']}：{txt}{extra}"

    def as_results(hs, via):
        return {"results": [{"chunk_id": h["chunk_id"], "source": "cns-book-2022",
                             "title": title_of("cns-book-2022"), "page": h["page"],
                             "text": show(h), "score": 1.0, "via": via} for h in hs],
                "note": None}

    # 第一层：别名/主体精确匹配（纯字符串，毫秒级，不调模型）
    hs = facts_match(query, limit=k)
    if hs:
        if verify_on:
            hs = verify(query, hs)
            if not hs:
                return {"results": [], "note": "候选都对不上问题，kb 不作答"}
        return as_results(hs, "alias")

    # 第二层：把口语翻成书中用词再试一次（单次无状态调用）
    try:
        from kb.rewrite import terms as _rewrite
        for t in _rewrite(query)[:3]:
            hs = facts_match(t, limit=k)
            if hs:
                if verify_on:
                    hs = verify(query, hs)
                    if not hs:
                        return {"results": [], "note": "候选都对不上问题，kb 不作答"}
                return as_results(hs, "rewrite")
    except Exception:
        pass

    # 第三层：BM25 + 向量 双路召回，RRF 融合后再重排
    bm_scores = bm.score(q)
    bm_hits = [i for _, i in bm_scores[:30]]
    order = list(bm_hits)
    used_vec = False
    vec = _vectors()
    if vec:
        try:
            import numpy as np
            from kb.embed import encode
            V, ids = vec
            pos = {r["id"]: k for k, r in enumerate(rows)}
            qv = encode([q])[0]
            cos = V @ qv
            # 余弦低于阈值的不算召回，否则向量会把"毫无关系"的块也带进来，拒答就失效了
            ranked = [(float(cos[k]), ids[k]) for k in np.argsort(-cos)[:30] if ids[k] in pos]
            near = [pos[cid] for sc, cid in ranked if sc >= 0.58]
            if not near and (not bm_scores or bm_scores[0][0] < MIN_SCORE):
                return {"results": [], "note": "语料里没有相关块"}
            fused = {}
            for rank, i in enumerate(bm_hits):
                fused[i] = fused.get(i, 0.0) + 1.0 / (60 + rank + 1)
            for rank, i in enumerate(near):
                fused[i] = fused.get(i, 0.0) + 1.0 / (60 + rank + 1)
            order = [i for i, _ in sorted(fused.items(), key=lambda x: -x[1])]
            used_vec = bool(near)
        except Exception:
            order = bm_hits
    cand = [(1.0, i) for i in order[:30]]

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
             "page": rows[i]["page"], "text": rows[i]["text"], "score": round(s, 2),
             "via": ("hybrid+" if used_vec else "") + ("rerank" if rr else "bm25")}
            for s, i in hits
        ],
        "note": None if hits else "语料里没有命中，调用方应拒答而不是让模型编",
    }


@mcp.tool()
def search_guideline(query: str, k: int = 5) -> dict:
    """按自然语言查指南原文。返回带 source/page 的片段；没有就返回空。"""
    return search(query, k)


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