# -*- coding: utf-8 -*-
"""分批 OCR：python build/ocr_pages.py 起始页 结束页（1-based，含两端）"""
import sys, os, time
sys.stdout.reconfigure(encoding="utf-8")
import pymupdf
from rapidocr_onnxruntime import RapidOCR

PDF = r"D:\project\2022年中国居民膳食指南 (中国营养学会).pdf"
OUT = r"D:\project\fitloop-kb\corpus\raw\cns-book-2022"
os.makedirs(OUT, exist_ok=True)

a = int(sys.argv[1]) if len(sys.argv) > 1 else 10
b = int(sys.argv[2]) if len(sys.argv) > 2 else 21
doc = pymupdf.open(PDF)
ocr = RapidOCR()
t0, done = time.time(), 0
for pno in range(a - 1, min(b, doc.page_count)):
    fp = os.path.join(OUT, f"p{pno+1:03d}.txt")
    if os.path.exists(fp):
        continue
    pix = doc[pno].get_pixmap(dpi=200)
    res, _ = ocr(pix.tobytes("png"))
    open(fp, "w", encoding="utf-8").write("".join(x[1] for x in res) if res else "")
    done += 1
spent = time.time() - t0
print(f"新增 {done} 页，{spent:.0f}s（{spent/max(1,done):.1f}s/页），累计 {len(os.listdir(OUT))} 页")
