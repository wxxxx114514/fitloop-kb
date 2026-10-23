# -*- coding: utf-8 -*-
"""全量抽取：609 块 → 结构化事实，每条都用原文校验。进度实时打印。"""
import sys, os, re, json, sqlite3, time
from concurrent.futures import ThreadPoolExecutor, as_completed
sys.path.insert(0, r"D:\project\fitloop-kb")
sys.path.insert(0, r"D:\project\fitloop")
sys.stdout.reconfigure(encoding="utf-8")
import app
from kb.retrieve import load

ROOT = r"D:\project\fitloop-kb"
DB = os.path.join(ROOT, "kb.db")

SYS = """从《中国居民膳食指南》原文中抽取“推荐摄入量/推荐做法”类事实。只输出 JSON：
{"facts":[{"subject":"主体","alias":["口语别名"],"metric":"指标","value":"数值","unit":"单位","quote":"原文片段"}]}
要求：
1. value 必须能在原文里逐字找到（含数字与符号），找不到就别输出这条
2. alias 给 2~4 个普通人会说的口语词
3. 只抽推荐量/上限/占比，不抽患病率、消费量调查等背景数据
4. 原文没有具体数值的直接返回 {"facts":[]}
"""

def norm(t): return re.sub(r"\s+", "", t)

def extract(client, row):
    msgs = [{"role": "system", "content": SYS},
            {"role": "user", "content": "原文：\n" + row["text"][:900]}]
    d = app._json_msgs(msgs, max_tokens=700)
    out, bad = [], 0
    for f in (d.get("facts") or []):
        v = str(f.get("value") or "").strip()
        if v and norm(v) in norm(row["text"]):
            out.append((row["id"], row["page"], str(f.get("subject") or ""),
                        str(f.get("metric") or ""), v, str(f.get("unit") or ""),
                        json.dumps(f.get("alias") or [], ensure_ascii=False)))
        else:
            bad += 1
    return out, bad

def main():
    rows = load()
    client = app._client()
    con = sqlite3.connect(DB)
    con.execute("DROP TABLE IF EXISTS facts")
    con.execute("""CREATE TABLE facts(id INTEGER PRIMARY KEY, chunk_id TEXT, page INT,
                   subject TEXT, metric TEXT, value TEXT, unit TEXT, alias TEXT)""")
    total, bad, done = [], 0, 0
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = {ex.submit(extract, client, r): r for r in rows}
        for fut in as_completed(futs):
            try:
                out, b = fut.result()
                total.extend(out); bad += b
            except Exception:
                pass
            done += 1
            if done % 50 == 0:
                print(f"{done}/{len(rows)}  已抽 {len(total)} 条  丢弃 {bad}  用时 {time.time()-t0:.0f}s", flush=True)
    con.executemany("INSERT INTO facts(chunk_id,page,subject,metric,value,unit,alias) VALUES (?,?,?,?,?,?,?)", total)
    con.commit(); con.close()
    print(f"完成：{len(total)} 条，校验丢弃 {bad} 条，用时 {time.time()-t0:.0f}s")

if __name__ == "__main__":
    main()
