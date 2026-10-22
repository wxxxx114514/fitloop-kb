# -*- coding: utf-8 -*-
"""按 sources.yaml 抓语料：记录 sha256 / content-type / 最终 URL。
抓不到就标 unavailable，不让构建带着空 chunk 往下跑。"""
import os, sys, json, time, hashlib, urllib.request, urllib.error
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RAW = os.path.join(ROOT, "corpus", "raw")
MANIFEST = os.path.join(ROOT, "corpus", "manifest.json")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) fitloop-kb/0.1"}


def download(url, tries=3, timeout=45):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            r = urllib.request.urlopen(req, timeout=timeout)
            body = r.read()
            return {"ok": True, "body": body, "final_url": r.geturl(),
                    "content_type": r.headers.get("Content-Type", ""), "status": r.status}
        except Exception as e:
            last = f"{type(e).__name__}: {str(e)[:80]}"
            time.sleep(1.5 * (i + 1))
    return {"ok": False, "error": last}


def main():
    os.makedirs(RAW, exist_ok=True)
    cfg = yaml.safe_load(open(os.path.join(ROOT, "corpus", "sources.yaml"), encoding="utf-8"))
    manifest = {"version": 1, "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"), "items": []}

    for s in cfg.get("sources", []):
        sid = s["id"]
        res = download(s["url"])
        item = {"id": sid, "org": s.get("org"), "year": s.get("year"),
                "kind": s.get("kind"), "url": s["url"]}
        if not res["ok"]:
            item.update(status="unavailable", error=res["error"])
            print(f"FAIL  {sid:<22}{res['error'][:60]}")
            manifest["items"].append(item)
            continue

        body = res["body"]
        if body[:5] == b"%PDF-":
            ext = "pdf"
        elif s.get("kind") in ("md", "html"):
            ext = s["kind"]
        else:
            ext = "html"
        path = os.path.join(RAW, f"{sid}.{ext}")
        open(path, "wb").write(body)

        # 内容校验：200 OK 不代表拿到了正文（反爬挑战页 / 落地页都会是 200）
        if ext in ("html", "md"):
            text = body.decode("utf-8", "ignore")
        else:
            try:                       # PDF 先把文字抽出来再校验
                import pymupdf
                doc = pymupdf.open(stream=body, filetype="pdf")
                text = "\n".join(p.get_text() for p in doc)
                item["pdf_pages"] = doc.page_count
            except Exception as e:
                text = ""
                item["pdf_error"] = f"{type(e).__name__}: {str(e)[:60]}"
        missing = [k for k in (s.get("expect_keywords") or []) if k not in text]
        too_small = len(body) < int(s.get("min_bytes") or 0)

        item.update(sha256=hashlib.sha256(body).hexdigest(),
                    bytes=len(body), ext=ext, final_url=res["final_url"],
                    content_type=res["content_type"], path=os.path.relpath(path, ROOT))

        if too_small or missing:
            item.update(status="unusable",
                        reason=("太小" if too_small else "") +
                               (("缺关键词 " + ",".join(missing)) if missing else ""))
            print(f"SHALLOW {sid:<20}{len(body):>9,} B  缺 {missing or '（太小）'}")
        else:
            item.update(status="ok")
            print(f"OK    {sid:<22}{len(body):>9,} B  .{ext}  sha256={item['sha256'][:12]}")
        manifest["items"].append(item)

    json.dump(manifest, open(MANIFEST, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    ok = sum(1 for i in manifest["items"] if i["status"] == "ok")
    print(f"\n{ok}/{len(manifest['items'])} 成功，清单写到 corpus/manifest.json")
    return 0 if ok == len(manifest["items"]) else 1


if __name__ == "__main__":
    sys.exit(main())