"""Read every cited URL again with the documentation crawler and log individual outcomes."""
import argparse
import json
from concurrent.futures import ThreadPoolExecutor,as_completed
from fetch import ROOT,fetch,receipt,save,utc

def read(p):
    return json.loads(p.read_text(encoding="utf-8-sig"))
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh",action="store_true")
    args=parser.parse_args()
    sources=set()
    for path in sorted((ROOT/"review").glob("*.json")):
        for r in read(path):
            sources.update(s["url"] for s in r["sources"])
    sources.update(p["url"] for p in read(ROOT/"verification/reference.json"))
    sources.update(p["url"] for p in read(ROOT/"review-corrections.json"))
    sources.update(p["url"] for p in read(ROOT/"verification/holdout-reference.json"))
    results=[]
    with ThreadPoolExecutor(max_workers=8) as pool:
        for f in as_completed([pool.submit(fetch,u,args.refresh) for u in sorted(sources)]):
            results.append(receipt(f.result()))
    save(ROOT/"runs/source-checks.json",sorted(results,key=lambda p:p["url"]))
    print("Checked",len(results),"citations at",utc(),flush=True)
if __name__=="__main__":
    main()
