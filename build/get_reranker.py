# -*- coding: utf-8 -*-
"""流式下载 reranker ONNX：边下边写，能看进度、能断点续传。"""
import sys, os, time, urllib.request
sys.stdout.reconfigure(encoding="utf-8")
px = "http://127.0.0.1:7897"
op = urllib.request.build_opener(urllib.request.ProxyHandler({"http": px, "https": px}))
D = r"D:\project\fitloop-kb\.models\reranker"
os.makedirs(os.path.join(D, "onnx"), exist_ok=True)
base = "https://huggingface.co/BAAI/bge-reranker-base/resolve/main/"
files = ["onnx/model.onnx", "tokenizer.json", "tokenizer_config.json", "config.json", "special_tokens_map.json"]

for f in files:
    p = os.path.join(D, f.replace("/", os.sep))
    if os.path.exists(p) and os.path.getsize(p) > 0:
        print("已有", f, f"{os.path.getsize(p)/1024/1024:.0f} MB", flush=True); continue
    t0, done = time.time(), 0
    r = op.open(urllib.request.Request(base + f, headers={"User-Agent": "Mozilla/5.0"}), timeout=600)
    total = int(r.headers.get("Content-Length") or 0)
    tmp = p + ".part"
    with open(tmp, "wb") as fh:
        while True:
            buf = r.read(1024 * 512)
            if not buf:
                break
            fh.write(buf); done += len(buf)
            if total and done % (20 * 1024 * 1024) < 512 * 1024:
                print(f"  {f}: {done/1024/1024:.0f}/{total/1024/1024:.0f} MB", flush=True)
    os.replace(tmp, p)
    print(f"下载 {f}: {done/1024/1024:.1f} MB, {time.time()-t0:.0f}s", flush=True)
print("全部完成", flush=True)
