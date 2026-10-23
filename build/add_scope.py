# -*- coding: utf-8 -*-
"""周期 v2：以 metric 字段里的周期为准，没有才看邻近文本（窗口 15 字）。
另外把「每周量」换算成每日当量，两条都存。"""
import sys, re, sqlite3
sys.path.insert(0, "D:/project/fitloop-kb")
sys.stdout.reconfigure(encoding="utf-8")
from kb.retrieve import load

DB = r"D:\project\fitloop-kb\kb.db"
text = {r["id"]: re.sub(r"\s+", "", r["text"]) for r in load()}
WEEK, MONTH = ("每周", "一周", "周摄"), ("每月", "一个月")

def scope_of(metric, t, val):
    m = metric or ""
    if any(w in m for w in WEEK):  return "week"
    if any(w in m for w in MONTH): return "month"
    if any(w in m for w in ("每天", "每日", "一天")): return "day"
    v = re.sub(r"\s+", "", str(val))
    i = t.find(v)
    if i < 0: return "day"
    seg = t[max(0, i - 15): i + len(v) + 15]
    for words, name in ((WEEK, "week"), (MONTH, "month")):
        if any(w in seg for w in words): return name
    return "day"

def to_daily(val, scope):
    m = re.match(r"^(\d+(?:\.\d+)?)\s*[~\-]\s*(\d+(?:\.\d+)?)\s*(.*)$", val)
    if not m or scope == "day":
        return None
    lo, hi, rest = float(m.group(1)), float(m.group(2)), m.group(3)
    # 只对重量/体积做换算；kg、次、杯这些换算成"每天"没有意义
    unit = rest.strip().lower()
    if not any(unit.startswith(u) for u in ("g", "克", "ml", "毫升", "毫克", "mg")):
        return None
    div = 7 if scope == "week" else 30
    return f"{lo/div:.0f}~{hi/div:.0f}{rest}"

def main():
    con = sqlite3.connect(DB)
    cols = [r[1] for r in con.execute("PRAGMA table_info(facts)")]
    if "scope" not in cols:   con.execute("ALTER TABLE facts ADD COLUMN scope TEXT")
    if "per_day" not in cols: con.execute("ALTER TABLE facts ADD COLUMN per_day TEXT")
    rows = con.execute("SELECT id, chunk_id, metric, value, unit FROM facts").fetchall()
    stat = {}
    for fid, cid, metric, val, unit in rows:
        t = text.get(cid, "")
        full = re.sub(r"\s+", "", str(val)) + re.sub(r"\s+", "", str(unit or ""))
        sc = scope_of(metric, t, full if full in t else str(val))
        con.execute("UPDATE facts SET scope=?, per_day=? WHERE id=?",
                    (sc, to_daily(full, sc), fid))
        stat[sc] = stat.get(sc, 0) + 1
    con.commit()
    print("周期分布:", stat)
    for r in con.execute("SELECT page,subject,value,unit,scope,per_day FROM facts WHERE scope!='day' LIMIT 6"):
        print(f"  p{r[0]} {r[1]} {r[2]}{r[3] or ''} [{r[4]}] → 每天 {r[5]}")
    con.close()

if __name__ == "__main__":
    main()