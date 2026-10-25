import os, sys
sys.stdout.reconfigure(encoding="utf-8")
cands = [
    r"D:\project\fitloop-kb\.models\models--Qdrant--bge-small-zh-v1.5",
    r"D:\project\fitloop-kb\.models\fe\models--Qdrant--bge-small-zh-v1.5",
    r"C:\Users\wxxxx\AppData\Local\Temp\dsh-GBXm0q\fastembed_cache\models--Qdrant--bge-small-zh-v1.5",
]
for c in cands:
    if not os.path.isdir(c):
        print("不存在:", c); continue
    tot = 0; hit = []
    for root, _, files in os.walk(c):
        for f in files:
            p = os.path.join(root, f)
            sz = os.path.getsize(p); tot += sz
            if f.endswith((".onnx", ".json", ".txt")) and sz > 1000:
                hit.append((f, round(sz/1024/1024, 1)))
    print(f"{c}\n   合计 {tot/1024/1024:.1f} MB  关键文件 {hit[:4]}")
