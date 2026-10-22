# -*- coding: utf-8 -*-
"""OCR 一页，返回带坐标的框。存成 JSON 当后续所有解析算法的原始资产。"""
import sys, os, json
sys.stdout.reconfigure(encoding="utf-8")
import pymupdf
from rapidocr_onnxruntime import RapidOCR

PDF = r"D:\project\2022年中国居民膳食指南 (中国营养学会).pdf"
OUT = r"D:\project\fitloop-kb\corpus\boxes"
os.makedirs(OUT, exist_ok=True)

def ocr_page(doc, ocr, pno, dpi=200):
    pix = doc[pno].get_pixmap(dpi=dpi)
    res, _ = ocr(pix.tobytes("png"))
    boxes = []
    for box, text, score in (res or []):
        xs = [p[0] for p in box]; ys = [p[1] for p in box]
        boxes.append({"x0": round(min(xs), 1), "y0": round(min(ys), 1),
                      "x1": round(max(xs), 1), "y1": round(max(ys), 1),
                      "t": text.strip(), "s": round(float(score), 3)})
    return {"page": pno + 1, "w": pix.width, "h": pix.height, "boxes": boxes}

if __name__ == "__main__":
    args = [int(x) for x in sys.argv[1:]]
    if len(args) == 2 and args[0] < args[1]:
        pages = list(range(args[0], args[1] + 1))
    else:
        pages = args or [11, 20, 27]
    doc = pymupdf.open(PDF); ocr = RapidOCR()
    for p in pages:
        fp = os.path.join(OUT, f"p{p:03d}.json")
        if os.path.exists(fp):
            print("已有", p); continue
        d = ocr_page(doc, ocr, p - 1)
        json.dump(d, open(fp, "w", encoding="utf-8"), ensure_ascii=False)
        print(f"p{p}: {len(d['boxes'])} 个框, {d['w']}x{d['h']}")