"""Re-score the first published release on the later, non-overlapping 10-app check."""
import hashlib
import json
import subprocess
from pathlib import Path
from fetch import ROOT,save
from publish_data import judge,read

def main():
    manifest=read(ROOT/"verification/holdout.json")
    ref=manifest["frozen_commit"]
    raw=subprocess.check_output(["git","show",ref+":docs/data/apps.json"],cwd=ROOT)
    assert hashlib.sha256(raw.replace(b"\r\n",b"\n")).hexdigest()==manifest["data_sha256_lf"]
    frozen=json.loads(raw)
    final=read(ROOT/"docs/data/apps.json")
    probes=read(ROOT/"verification/holdout-reference.json")
    results=[]
    for p in probes:
        name=frozen[p["id"]-1]["name"]
        field=p["field"]
        before=frozen[p["id"]-1][field]
        after=final[p["id"]-1][field]
        results.append({**p,"name":name,"frozen":before,"published":after,"frozen_correct":judge(before,p),"published_correct":judge(after,p)})
    manifest.update(apps=len({p["id"] for p in probes}),total=len(probes),frozen_hits=sum(r["frozen_correct"] for r in results),
                    published_hits=sum(r["published_correct"] for r in results),observations=results)
    save(ROOT/"verification/holdout.json",manifest)
if __name__=="__main__":main()
