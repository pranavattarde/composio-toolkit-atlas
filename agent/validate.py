"""Check the released catalog, evidence contract, aggregates and browser payload offline."""
import csv
import json
from collections import Counter
from pathlib import Path
from bs4 import BeautifulSoup
from fetch import ROOT
from publish_data import VERDICTS, judge
from research import inputs

def main():
    data=ROOT/"docs/data"
    def read(file): return json.loads((data/file).read_text(encoding="utf-8-sig"))
    apps=read("apps.json"); summary=read("summary.json"); first=read("first-pass.json")
    assert [(r["id"],r["name"],r["category"],r["website_hint"]) for r in apps]==[(r["id"],r["name"],r["category"],r["website_hint"]) for r in inputs()]
    assert len(apps)==100 and len(first)==100 and len({r["category"] for r in apps})==10
    assert Counter(r["verdict"] for r in apps)==summary["verdict"] and set(summary["verdict"])<=set(VERDICTS)
    for r in apps:
        assert r["sources"] and r["toolkit"] and r["last_checked"] and r["unknowns"]
        assert all(s["url"].startswith(("https://","http://")) and s["claims"] and s["note"] for s in r["sources"])
        for field,tag in [("third_party_mcp","mcp_third_party"),("official_mcp","mcp_official")]:
            assert r[field]!="Verified" or any(tag in s["claims"] for s in r["sources"])
        assert all(s["fetch_status"] not in {"http_404","http_410","unchecked"} for s in r["sources"])
    for key in ["auth","api","access","surface","blocker_type"]:
        values=Counter()
        for r in apps: values.update(r[key] if isinstance(r[key],list) else [r[key]])
        assert dict(values)==summary[key]
    assert sum(c["count"] for c in summary["categories"])==100
    for c in summary["categories"]:
        assert c["count"]==sum(c["verdict"].values())==sum(c["access"].values())==10
    audit=read("verification.json")
    assert len({apps[q["id"]-1]["category"] for q in audit})==10
    assert {apps[q["id"]-1]["verdict"] for q in audit}==set(summary["verdict"])
    for q in audit:
        assert judge(first[q["id"]-1][q["field"]],q)==q["first_correct"]
        assert judge(apps[q["id"]-1][q["field"]],q)==q["final_correct"]
    assert sum(q["first_correct"] for q in audit)==summary["first_hits"]
    assert sum(q["final_correct"] for q in audit)==summary["final_hits"]
    assert summary["tested_fields"]==len(audit)
    with (data/"apps.csv").open(encoding="utf-8-sig",newline="") as f:
        csv_rows=list(csv.DictReader(f))
    assert len(csv_rows)==len(apps) and all(json.loads(c["sources"])==r["sources"] for c,r in zip(csv_rows,apps))
    page=BeautifulSoup((ROOT/"docs/index.html").read_text(encoding="utf8"),"html.parser")
    embedded=json.loads(page.select_one("#dataset").string)
    assert embedded["apps"]==apps and embedded["summary"]==summary and embedded["checks"]==audit
    for a in page.select("a[href]"):
        url=a["href"]
        if url.startswith("data/"): assert (ROOT/"docs"/url).is_file()
    print(f'PASS: {len(apps)} apps, 10 categories, {summary["reviewed_sources"]} cited URLs, {len(audit)} scored checks, CSV/JSON/HTML agree.')
if __name__=="__main__": main()

