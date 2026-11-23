import json
from pathlib import Path
from fetch import ROOT
def main():
    data=ROOT/"docs/data"
    template=(ROOT/"study/index.template.html").read_text(encoding="utf-8-sig")
    payload={k:json.loads((data/f).read_text(encoding="utf-8-sig")) for k,f in {
        "apps":"apps.json","summary":"summary.json","checks":"verification.json","run":"run.json"}.items()}
    payload["browser"]=json.loads((ROOT/"verification/browser-observations.json").read_text(encoding="utf-8-sig"))
    payload["holdout"]=json.loads((ROOT/"verification/holdout.json").read_text(encoding="utf-8-sig"))
    for key,path in [("__CSS__","style.css"),("__JS__","app.js")]:
        template=template.replace(key,(ROOT/"study"/path).read_text(encoding="utf-8-sig"))
    template=template.replace("__PAYLOAD__",json.dumps(payload,ensure_ascii=False,separators=(",",":")).replace("<","\\u003c"))
    (ROOT/"docs/index.html").write_text(template,encoding="utf-8")
    (ROOT/"docs/.nojekyll").touch()
if __name__=="__main__": main()
