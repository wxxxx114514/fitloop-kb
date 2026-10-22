# -*- coding: utf-8 -*-
"""基于几何规则的版面分析（XY-Cut 变体 + 启发式块分类）。

输入：build/ocr_boxes.py 产出的 {"page","w","h","boxes"} JSON
输出：按阅读顺序排列的块，每块 type = text / table / figure

三条核心规则（都来自业界规则型版面分析）：
1. 竖直中缝：先找"从头到尾没有文字穿过"的空白带 → 据此切左右栏
2. 聚行：中心 y 差 < 半个行高才算同一行（扫描件有倾斜）
3. 聚列：x 起点差 < 1.5 倍平均字宽才算同一列
"""
import sys, json, os, re
from statistics import median

MIN_SCORE = 0.5
MIN_W_BOX = 4

def load(p):
    return json.load(open(p, encoding="utf-8"))

def clean_boxes(page, pad=0):
    w, h = page["w"], page["h"]
    out = []
    for b in page["boxes"]:
        if b["s"] < MIN_SCORE: continue
        if b["x1"] - b["x0"] < MIN_W_BOX: continue
        # 页边距外的（扫描歪斜产生的边角）丢掉
        if b["x0"] < pad or b["x1"] > w - pad: continue
        out.append(b)
    return out

def vertical_gutter(boxes, w):
    """找竖直中缝：把每个框投影到 x 轴，找中间区域最宽的空白带。"""
    occ = [0] * (w + 1)
    for b in boxes:
        for x in range(int(b["x0"]), int(b["x1"]) + 1):
            occ[x] = 1
    lo, hi = int(w * 0.30), int(w * 0.70)
    best, cur, start = (0, 0, 0), 0, None
    for x in range(lo, hi):
        if occ[x] == 0:
            if start is None: start = x
            cur += 1
            if cur > best[0]: best = (cur, start, x)
        else:
            cur, start = 0, None
    return (best[1], best[2]) if best[0] >= 25 else None

def group_rows(boxes):
    if not boxes: return []
    hs = [b["y1"] - b["y0"] for b in boxes]
    tol = max(6, median(hs) * 0.5)
    bs = sorted(boxes, key=lambda b: (b["y0"] + b["y1"]) / 2)
    rows, cur = [], [bs[0]]
    for b in bs[1:]:
        cy = (b["y0"] + b["y1"]) / 2
        last = (cur[-1]["y0"] + cur[-1]["y1"]) / 2
        if abs(cy - last) <= tol:
            cur.append(b)
        else:
            rows.append(sorted(cur, key=lambda i: i["x0"]))
            cur = [b]
    rows.append(sorted(cur, key=lambda i: i["x0"]))
    return rows

def looks_numeric(t):
    t = t.strip()
    if not t: return False
    return len(re.findall(r"[\d.%]", t)) / len(t) > 0.6 and len(t) <= 12

def detect_table(rows):
    """连续 ≥3 行、每行 ≥3 个框、列 x 位置对齐 → 判为表格。"""
    def aligned(rs):
        """返回列坐标列表（对齐的 x 中心），不齐返回 None。"""
        if len(rs) < 3: return None
        if min(len(r) for r in rs) < 3: return None
        widths = [b["x1"] - b["x0"] for r in rs for b in r]
        cw = median(widths)
        cols = []
        for b in rs[0]:
            cx = (b["x0"] + b["x1"]) / 2
            if all(any(abs((c["x0"] + c["x1"]) / 2 - cx) < cw * 1.5 for c in r) for r in rs[1:]):
                cols.append(cx)
        return cols if len(cols) >= 3 else None

    tables, i = [], 0
    while i < len(rows):
        found = None
        for j in range(len(rows), i + 2, -1):
            cols = aligned(rows[i:j])
            if cols:
                found = (i, j, cols); break
        if found:
            tables.append(found); i = found[1]
        else:
            i += 1
    return tables

def to_markdown(rows):
    ncol = max(len(r) for r in rows)
    lines = []
    for k, r in enumerate(rows):
        cells = [b["t"] for b in r] + [""] * (ncol - len(r))
        lines.append("| " + " | ".join(cells) + " |")
        if k == 0:
            lines.append("|" + "---|" * ncol)
    return "\n".join(lines)

def parse_page(page):
    boxes = clean_boxes(page)
    if not boxes:
        return []

    # 先看整页是不是被一张表占满（表格页不该被"中缝"切成左右）
    full_rows = group_rows(boxes)
    full_tables = detect_table(full_rows)
    table_dominated = any((j - i) >= 4 for i, j, _ in full_tables)

    gutter = None if table_dominated else vertical_gutter(boxes, page["w"])
    if gutter:
        g0, g1 = gutter
        left = [b for b in boxes if b["x1"] <= g0 + 5]
        right = [b for b in boxes if b["x0"] >= g1 - 5]
        span = [b for b in boxes if b not in left and b not in right]   # 通栏
        cols = [("full", span)] + [("left", left), ("right", right)]
    else:
        cols = [("full", boxes)]

    blocks = []
    for name, bs in cols:
        if not bs: continue
        rows = group_rows(bs)
        tables = detect_table(rows)
        ti = {t[0]: t for t in tables}
        k = 0
        while k < len(rows):
            if k in ti:
                i, j, _ = ti[k]
                blocks.append({"type": "table", "col": name, "text": to_markdown(rows[i:j])})
                k = j
            else:
                txt = "".join(b["t"] for b in rows[k])
                if txt.strip():
                    blocks.append({"type": "text", "col": name, "text": txt})
                k += 1
    return mark_figures(blocks)


def is_pure_number(t):
    t = t.strip()
    return bool(t) and len(t) <= 8 and re.fullmatch(r"[\d.,%]+", t) is not None


def mark_figures(blocks):
    """连续 ≥4 个纯数字小块 → 判为图表坐标轴，整段丢弃，只保留图注。"""
    out, i = [], 0
    while i < len(blocks):
        if blocks[i]["type"] == "text" and is_pure_number(blocks[i]["text"]):
            j = i
            while j < len(blocks) and blocks[j]["type"] == "text" and is_pure_number(blocks[j]["text"]):
                j += 1
            if j - i >= 4:
                out.append({"type": "figure", "col": blocks[i]["col"],
                            "text": f"[图表区域，{j-i} 个坐标/数据标签已剔除]"})
                i = j
                continue
        out.append(blocks[i])
        i += 1
    return out

if __name__ == "__main__":
    D = r"D:\project\fitloop-kb\corpus\boxes"
    for f in sys.argv[1:]:
        p = os.path.join(D, f)
        blocks = parse_page(load(p))
        print(f"=== {f} : {len(blocks)} 块 ===")
        for b in blocks[:12]:
            print(f"  [{b['type']}/{b['col']}] {b['text'][:70]}")
        print()