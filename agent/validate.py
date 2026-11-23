"""Check the released catalog, evidence contract, aggregates and browser payload offline."""
import csv
import json
from collections import Counter
from pathlib import Path
from bs4 import BeautifulSoup
from evidence_screen import confidence, inspect_app
from fetch import ROOT
from publish_data import VERDICTS, judge
from research import inputs

def main():
    data=ROOT/"docs/data"
    def read(file): return json.loads((data/file).read_text(encoding="utf-8-sig"))
    apps=read("apps.json"); summary=read("summary.json"); first=read("first-pass.json")
    receipts={r["url"]:r for r in read("source-checks.json")}
    assert [(r["id"],r["name"],r["category"],r["website_hint"]) for r in apps]==[(r["id"],r["name"],r["category"],r["website_hint"]) for r in inputs()]
    assert len(apps)==100 and len(first)==100 and len({r["category"] for r in apps})==10
    assert Counter(r["verdict"] for r in apps)==summary["verdict"] and set(summary["verdict"])<=set(VERDICTS)
    for r in apps:
        assert r["sources"] and r["toolkit"] and r["last_checked"] and r["unknowns"]
        assert all(s["url"].startswith(("https://","http://")) and s["claims"] and s["note"] for s in r["sources"])
        for field,tag in [("third_party_mcp","mcp_third_party"),("official_mcp","mcp_official")]:
            assert r[field]!="Verified" or any(tag in s["claims"] for s in r["sources"])
        assert all(s["fetch_status"] not in {"http_404","http_410","unchecked"} for s in r["sources"])
        assert r["evidence_screen"]==inspect_app(r,receipts)
        assert r["confidence"]==confidence(r,r["evidence_screen"])
    for key in ["auth","api","access","surface","blocker_type","confidence","remote_api","official_mcp","third_party_mcp"]:
        values=Counter()
        for r in apps: values.update(r[key] if isinstance(r[key],list) else [r[key]])
        assert dict(values)==summary[key]
    assert sum(c["count"] for c in summary["categories"])==100
    for c in summary["categories"]:
        assert c["count"]==sum(c["verdict"].values())==sum(c["access"].values())==10
        members=[r for r in apps if r["category"]==c["name"]]
        assert Counter(r["verdict"] for r in members)==c["verdict"]
        assert Counter(r["access"] for r in members)==c["access"]
    ready=[r for r in apps if r["verdict"]=="READY"]
    assert summary["ready_listed"]==sum(bool(r["composio_listing"]) for r in ready)
    gaps=[r for r in ready if not r["composio_listing"]]
    assert summary["catalog_gap_candidates"]==[r["id"] for r in gaps]
    paths=("Self-serve free","Self-serve trial","Local/open source")
    shortlist=[next((r["id"] for r in gaps if r["access"]==path),None) for path in paths]
    assert summary["shortlist"]==[app_id for app_id in shortlist if app_id is not None]
    assert summary["reviewed_sources"]==len({s["url"] for r in apps for s in r["sources"]})
    assert summary["readable_sources"]==len({s["url"] for r in apps for s in r["sources"] if s["fetch_status"]=="readable"})
    assert summary["resolved_fields"]=={
        "auth":sum(bool(r["auth"]) for r in apps),
        "access":sum(r["access"]!="Unknown" for r in apps),
        "api":sum(bool(r["api"]) for r in apps),
    }
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
    holdout=embedded["holdout"]
    assert len(holdout["observations"])==holdout["total"]
    assert {q["id"] for q in holdout["observations"]}.isdisjoint(q["id"] for q in audit)
    assert sum(q["frozen_correct"] for q in holdout["observations"])==holdout["frozen_hits"]
    for q in holdout["observations"]:
        assert judge(q["frozen"],q)==q["frozen_correct"]
        assert judge(apps[q["id"]-1][q["field"]],q)==q["published_correct"]
    independent=read("stratified-audit.json")
    observations=independent["observations"]
    ids={q["id"] for q in observations}
    assert ids.isdisjoint(q["id"] for q in audit+holdout["observations"])
    categories=Counter(apps[app_id-1]["category"] for app_id in ids)
    assert len(categories)==10 and set(categories.values())=={2}
    for q in observations:
        index=q["id"]-1
        assert q["first_value"]==first[index][q["field"]]
        assert q["final_value"]==apps[index][q["field"]]
        for stage in ("first","prior","final"):
            assert judge(q[stage+"_value"],q)==q[stage+"_correct"]
    assert independent["scores"]==summary["independent"]=={
        "apps":len(ids),"claims":len(observations),"categories":len(categories),
        **{stage:sum(q[stage+"_correct"] for q in observations) for stage in ("first","prior","final")},
    }
    for a in page.select("a[href]"):
        url=a["href"]
        if url.startswith("data/"): assert (ROOT/"docs"/url).is_file()
    print(f'PASS: {len(apps)} apps, 10 categories, {summary["reviewed_sources"]} cited URLs, {len(audit)} scored checks, CSV/JSON/HTML agree.')
if __name__=="__main__": main()
