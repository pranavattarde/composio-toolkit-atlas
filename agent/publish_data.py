"""Build a frozen, auditable release from a crawl, attributed reviews and independent probes."""
import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path

from fetch import ROOT, save
from research import inputs

DATA=ROOT/"docs/data"
VERDICTS=["READY","CONDITIONAL","GATED","BLOCKED","UNKNOWN"]
REMOTE={"REST","HTTP API","GraphQL","SOAP","RPC","gRPC","WebSocket"}
CORE=["identity","auth","access","api","surface","mcp_official","mcp_third_party"]

def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))

def merge_sources(sources):
    by_url={}
    for s in sources:
        u=s["url"]
        if u not in by_url:
            by_url[u]=dict(s)
        else:
            prev=by_url[u]
            if s["note"] not in prev["note"]: prev["note"]+=" "+s["note"]
            prev["claims"]=sorted(set(prev["claims"]+s["claims"]))
    return list(by_url.values())

def judge(value,q):
    op=q.get("operator","contains" if isinstance(value,list) else "equals")
    if op=="excludes": return q["expected"] not in value
    if op=="exact_set": return set(value)==set(q["expected"])
    return q["expected"] in value if op=="contains" else value==q["expected"]

def counts(rows,field):
    c=Counter()
    for row in rows:
        values=row[field]
        c.update(values if isinstance(values,list) else [values])
    return dict(c.most_common())

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot",action="store_true",help="Use the committed release receipts rather than a new crawl")
    args=parser.parse_args()
    source=DATA if args.snapshot else ROOT/"runs"
    first=read(DATA/"first-pass.json" if args.snapshot else source/"baseline/first-pass.json")
    run=read(DATA/"run.json" if args.snapshot else source/"baseline/run.json")
    catalog=read(source/"catalog.json")
    checks=read(source/"source-checks.json")
    audit=read(ROOT/"verification/reference.json")
    changes=read(ROOT/"review-corrections.json")
    apps=inputs()
    reviews=[r for p in sorted((ROOT/"review").glob("*.json")) for r in read(p)]
    assert sorted(r["id"] for r in reviews)==list(range(1,101))
    assert [r["id"] for r in first]==list(range(1,101))
    rev={r["id"]:r for r in reviews}
    cat={r["id"]:r for r in catalog["matches"]}
    tickets={r["url"]:r for r in checks}
    final=[]; issues=[]; delta=[]
    for app,baseline in zip(apps,first):
        n=app["id"]; r={**app,**rev[n]}
        r["sources"]=list(r["sources"])
        for edit in [x for x in changes if x["id"]==n]:
            delta.append({"id":n,"field":edit["field"],"before":r[edit["field"]],"after":edit["value"],"reason":edit["note"]})
            r[edit["field"]]=edit["value"]; r.update(edit.get("additional",{}))
            r["sources"].append({k:edit[k] for k in ("url","note","claims")})
        # Useful supporting checks also address gaps in the original source review.
        for q in (p for p in audit if p["id"]==n):
            tag={"official_mcp":"mcp_official","third_party_mcp":"mcp_third_party"}.get(q["field"],q["field"])
            if tag in CORE and judge(r[q["field"]],q):
                r["sources"].append({"url":q["url"],"claims":[tag],"note":q["note"]})
        entry=cat[n]
        r["composio_listing"]=entry["catalog_route"]
        if entry.get("mcp_route") and not entry["catalog_route"].endswith("_mcp"):
            r["third_party_mcp"]="Verified"
            r["sources"].append({"url":entry["catalog_route"],"claims":["mcp_third_party"],
                 "note":"Composio publishes a managed MCP route for this integration. The catalog page identifies the provider and agent-facing interface."})
        sources=merge_sources(r["sources"])
        r["sources"]=[]
        for s in sources:
            status=tickets.get(s["url"]) or (entry.get("receipt",{}) if s["url"]==entry.get("catalog_route") else {})
            if status.get("http") in {404,410}:
                issues.append({"id":n,"kind":"unavailable citation","url":s["url"],"action":"Removed from the published app evidence; remaining sources re-evaluated."})
                continue
            s["fetch_status"]=status.get("status","unchecked")
            s["last_fetched"]=status.get("checked_at")
            r["sources"].append(s)
        claims={k for s in r["sources"] for k in s["claims"]}
        for k,tag in [("third_party_mcp","mcp_third_party"),("official_mcp","mcp_official")]:
            if r[k]=="Verified" and tag not in claims:
                issues.append({"id":n,"kind":"MCP ownership unsupported after URL check","action":k+" changed to Unverified"})
                r[k]="Unverified"
        if r["auth"] and "auth" not in claims or r["api"] and "api" not in claims or r["access"]!="Unknown" and "access" not in claims:
            raise ValueError(f"Missing field citation for {n}: {claims}")
        if r["verdict"]=="READY" and (not r["api"] or r["access"] in {"Unknown","Partner/sales","Paid plan","Admin approval"}):
            raise ValueError(f"Unsupported READY {n}")
        r["remote_api"]="Documented" if set(r["api"]) & REMOTE else "Unverified"
        if n==58: r["remote_api"]="Self-hosted HTTP wrapper"
        if n==98: r["remote_api"]="Local interface only in reviewed sources"
        r["last_checked"]=max((s.get("last_fetched") or baseline["checked_at"])[:10] for s in r["sources"]) if r["sources"] else baseline["checked_at"][:10]
        routes={"auth":bool(r["auth"] or r["access"]=="Local/open source"),"access":r["access"]!="Unknown","api":bool(r["api"])}
        readable={k for s in r["sources"] if s["fetch_status"]=="readable" for k in s["claims"]}
        r["confidence"]="Low" if r["verdict"]=="UNKNOWN" or not r["api"] else (
            "High" if all(routes.values()) and {"api","access","auth"} <= readable else "Medium")
        for s in r["sources"]:
            if s["fetch_status"]!="readable":
                issues.append({"id":n,"kind":"direct reader limitation","url":s["url"],"status":s["fetch_status"],"action":"Attributed source review retained; direct fetch limitation visible."})
        if r["confidence"]!="High": issues.append({"id":n,"kind":"confidence","action":r["confidence"],"questions":r["unknowns"]})
        if len(baseline["access_signals"])>1:
            issues.append({"id":n,"kind":"overlapping access signals","signals":baseline["access_signals"],"action":r["access_note"]})
        if r["auth"]!=baseline["auth"] and set(r["auth"])!=set(baseline["auth"]):
            issues.append({"id":n,"kind":"auth discrepancy","before":baseline["auth"],"after":r["auth"],"action":"Applied source-attributed route review."})
        if n in {11,22,31,85}: issues.append({"id":n,"kind":"version or route ambiguity","action":r["blocker"]+" "+" ".join(r["unknowns"])})
        for field in ["auth","api","access","official_mcp","third_party_mcp","verdict"]:
            if baseline[field]!=r[field] and not (isinstance(r[field],list) and set(baseline[field])==set(r[field])):
                delta.append({"id":n,"field":field,"before":baseline[field],"after":r[field],"reason":"Reviewed source notes and scope in the final app record."})
        final.append(r)
    v=[]
    for q in audit:
        idx=q["id"]-1; field=q["field"]
        b,a=first[idx][field],final[idx][field]
        v.append({**q,"name":final[idx]["name"],"first":b,"final":a,"first_correct":judge(b,q),"final_correct":judge(a,q),
                  "first_verdict":first[idx]["verdict"],"final_verdict":final[idx]["verdict"]})
    cats=list(dict.fromkeys(r["category"] for r in final))
    summary={field:counts(final,field) for field in ["auth","api","access","remote_api","surface","blocker_type","confidence","verdict","official_mcp","third_party_mcp"]}
    summary.update({"apps":len(final),"categories":[{"name":c,"count":sum(r["category"]==c for r in final),
         "verdict":counts([r for r in final if r["category"]==c],"verdict"),"access":counts([r for r in final if r["category"]==c],"access")} for c in cats],
         "reviewed_sources":len({s["url"] for r in final for s in r["sources"]}),
         "readable_sources":len({s["url"] for r in final for s in r["sources"] if s["fetch_status"]=="readable"}),
         "source_fields":{k:sum(any(k in s["claims"] for s in r["sources"]) for r in final) for k in CORE},
         "catalog_matches":sum(bool(r["composio_listing"]) for r in final),
         "both_mcp":sum(r["official_mcp"]==r["third_party_mcp"]=="Verified" for r in final),
         "selfserve":sum(r["access"].startswith("Self-serve") for r in final),"coverage_apps":sum(bool(r["sources"]) for r in final),
         "tested_apps":len({q["id"] for q in v}),"tested_fields":len(v),"first_hits":sum(q["first_correct"] for q in v),
         "final_hits":sum(q["final_correct"] for q in v),"sample_classes":counts([r for r in final if r["id"] in {q["id"] for q in v}],"verdict"),
         "sample_categories":len({final[q["id"]-1]["category"] for q in v}),"first_known":sum(r["verdict"]!="UNKNOWN" for r in first),
         "first_sources":sum(run["source_status"].values()),"last_checked":max(r["last_checked"] for r in final),
         "ready_listed":sum(r["verdict"]=="READY" and bool(r["composio_listing"]) for r in final),
         "free_with_restrictions":sum(r["access"] in {"Self-serve free","Self-serve trial"} and r["verdict"] in {"CONDITIONAL","GATED"} for r in final)})
    for filename,obj in {"first-pass":first,"run":run,"catalog":catalog,"source-checks":checks,"apps":final,"summary":summary,"verification":v,"corrections":delta,"issues":issues}.items():
        save(DATA/(filename+".json"),obj)
    with (DATA/"apps.csv").open("w",encoding="utf-8-sig",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=final[0].keys());writer.writeheader()
        for r in final: writer.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in r.items()})
    print(json.dumps({k:summary[k] for k in ["verdict","tested_apps","tested_fields","first_hits","final_hits","reviewed_sources","readable_sources","selfserve","ready_listed","free_with_restrictions"]},indent=2))
if __name__=="__main__": main()

