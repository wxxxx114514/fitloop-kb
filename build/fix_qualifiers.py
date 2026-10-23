# -*- coding: utf-8 -*-
"""限定词补齐 v2：按 value+unit+限定词 的完整形式去原文里找。"""
import sys, re, sqlite3
sys.path.insert(0, r"D:\project\fitloop-kb")
sys.stdout.reconfigure(encoding="utf-8")
from kb.retrieve import load

DB = r"D:\project\fitloop-kb\kb.db"
text = {r["id"]: re.sub(r"\s+", "", r["text"]) for r in load()}
QUAL = ("以上", "以下", "不少于", "不超过", "不多于")

con = sqlite3.connect(DB)
rows = con.execute("SELECT id, chunk_id, value, unit FROM facts").fetchall()
fixed = 0
for fid, cid, val, unit in rows:
    t = text.get(cid, "")
    v, u = re.sub(r"\s+", "", str(val)), re.sub(r"\s+", "", str(unit or ""))
    if any(v.endswith(q) for q in QUAL):
        continue
    for q in QUAL:
        full = v + u + q
        if full in t:
            con.execute("UPDATE facts SET value=?, unit='' WHERE id=?", (full, fid))
            fixed += 1
            break
con.commit()
print("补上限定词:", fixed, "条")
for r in con.execute("SELECT page,subject,value FROM facts WHERE subject LIKE '%食物种类%' LIMIT 3"):
    print("  ", r)
con.close()
