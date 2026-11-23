"""Generate a fresh first pass from public pages without consulting review annotations."""
import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlparse

from fetch import ROOT, fetch, receipt, save, utc, valid

AUTH = {
    "OAuth2": r"\boauth[\s-]*(?:2(?:\.0)?|authorization code)\b",
    "API key": r"\b(?:your|an?|the|generate|obtain|create|using|private|public)\s+(?:private |secret )?api[\s_-]?key\b",
    "Basic": r"\b(?:http basic auth(?:entication)?|basic authentication)\b",
    "Bearer token": r"\b(?:bearer (?:token|access_token)|authorization:\s*bearer|personal access token)\b",
    "Service account": r"\bservice account (?:key|credential|authentication|token)s?\b",
    "Other": r"\b(?:bot token|bot.{0,22}unique authentication token)\b",
}
API = {
    "REST": r"\brest(?:ful)?\s+(?:web\s+)?apis?\b",
    "GraphQL": r"\bgraphql\s+(?:api|endpoint|query)\b",
    "SOAP": r"\bsoap\s+(?:web service|api)\b",
    "HTTP API": r"\b(?:http[- ]based interface|https? api|json[- ]rpc api)\b",
    "CLI": r"\b(?:command[- ]line (?:interface|tool)|mermaid cli)\b",
    "SDK": r"\b(?:python|javascript|node\.js|official) sdk\b",
}
ACCESS = {
    "Partner/sales": r"(?:api access.{0,45}(?:contact (?:our |your )?(?:sales|representative)|partner approval)|(?:approved partners|partner approval).{0,60}api)",
    "Paid plan": r"(?:api access|api keys?).{0,50}(?:paid plans? only|requires? (?:a |an )?(?:paid|enterprise) plan)",
    "Admin approval": r"(?:only (?:an? )?(?:workspace |account )?admin.{0,60}(?:token|api key)|admin approval is required)",
    "Self-serve free": r"(?:free (?:of charge )?(?:for (?:both )?(?:users and )?developers|developer account|sandbox account)|free (?:access to|tier.{0,30}for) (?:the )?api)",
    "Self-serve trial": r"free trial.{0,50}(?:api access|api keys?)",
    "Self-serve (cost unverified)": r"\b(?:create|generate|creating|generating) (?:your |an? |new )?(?:personal access token|api key)\b",
}
REMOTE = {"REST","GraphQL","SOAP","HTTP API"}
EXCLUDE = re.compile(r"\b(?:deprecated|replac(?:e|es|ed)|no longer|does not support|is not supported)\b",re.I)
SCORE = [(r"authenticat|authoriz|api key|access token",6),(r"api reference|developer doc|api docs|developer portal",5),(r"getting started|quickstart|rest api|graphql|mcp server",4),(r"\bapi\b|pricing|developer",2)]

def inputs():
    with (ROOT/"input/apps.csv").open(encoding="utf-8-sig",newline="") as f:
        rows = [dict(r,id=int(r["id"])) for r in csv.DictReader(f)]
    assert [r["id"] for r in rows] == list(range(1,101))
    assert len({r["name"] for r in rows}) == 100 and set(Counter(r["category"] for r in rows).values()) == {10}
    return rows

def candidates(app, seeds):
    hint = app["website_hint"].split(" (")[0].strip()
    urls = list(seeds.get(str(app["id"]), []))
    if valid("https://"+hint) and " " not in hint:
        urls.append("https://"+hint)
    return list(dict.fromkeys(urls))

def related(origin, dest):
    a, b = urlparse(origin), urlparse(dest)
    if b.query or re.search(r"\.(?:pdf|png|svg|zip)$",b.path,re.I):
        return False
    if a.hostname == "github.com":
        return a.hostname == b.hostname and a.path.strip("/").split("/")[:2] == b.path.strip("/").split("/")[:2]
    host = a.hostname.removeprefix("www.")
    root = ".".join(host.split(".")[-2:])
    return b.hostname == root or b.hostname.endswith("."+root)

def discover(page):
    ranked = {}
    for label,url in page["links"]:
        if not related(page["final_url"],url):
            continue
        score = sum(val for pattern,val in SCORE if re.search(pattern,label,re.I))
        if score and not re.search(r"privacy|sign.in|login|blog/|/changelog|/community/",url,re.I):
            ranked[url] = max(ranked.get(url,0),score)
    return sorted(ranked,key=lambda u:(-ranked[u],len(u),u))

def signals(pages, patterns, field, evidence):
    found = []
    for name,pattern in patterns.items():
        for page in pages:
            content = page["title"] + ". " + page["text"]
            for m in re.finditer(pattern,content,re.I):
                before = content[max(0,m.start()-66):m.start()]
                after = content[m.end():m.end()+55]
                if EXCLUDE.search(before + m.group() + after):
                    continue
                excerpt = (before.split(" ",1)[-1] + m.group() + after.rsplit(" ",1)[0]).strip()
                evidence.append({"field":field,"value":name,"url":page["url"],"excerpt":excerpt[:200]})
                found.append(name)
                break
            if name in found:
                break
    return found

def research(app,seeds,cap,refresh):
    queue = candidates(app,seeds)
    visited, pages = set(), []
    while queue and len(pages)<cap:
        url = queue.pop(0)
        if url in visited:
            continue
        visited.add(url)
        page = fetch(url,refresh=refresh)
        pages.append(page)
        visited.add(page["final_url"])
        if page["status"]=="readable":
            queue.extend(u for u in discover(page) if u not in visited and u not in queue)
    good = [p for p in pages if p["status"]=="readable"]
    evidence = []
    auth = signals(good,AUTH,"auth",evidence)
    api = signals(good,API,"api",evidence)
    access_signals = signals(good,ACCESS,"access",evidence)
    access = access_signals[0] if access_signals else "Unknown"
    mcp = signals(good,{"Verified":r"(?:official.{0,28}MCP server|(?:our|the official) Model Context Protocol server)"},"official_mcp",evidence)
    verdict = "UNKNOWN"
    if set(api) & REMOTE:
        if access == "Partner/sales": verdict = "GATED"
        elif access in {"Admin approval","Paid plan"}: verdict = "CONDITIONAL"
        elif auth and access.startswith("Self-serve"): verdict = "READY"
    return {**app,"auth":auth,"api":api,"access":access,"official_mcp":"Verified" if mcp else "Unverified",
            "third_party_mcp":"Unverified","verdict":verdict,"evidence":evidence,
            "access_signals":access_signals,"sources":[receipt(p) for p in pages],"checked_at":utc()}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ids",help="Comma-separated app IDs. Default: all 100.")
    parser.add_argument("--pages",type=int,default=5)
    parser.add_argument("--workers",type=int,default=6)
    parser.add_argument("--out",type=Path,default=ROOT/"runs/latest")
    parser.add_argument("--refresh",action="store_true",help="Re-read selected apps and bypass page cache")
    args=parser.parse_args()
    if not 1<=args.workers<=10 or not 1<=args.pages<=20:
        parser.error("workers must be 1–10 and pages must be 1–20")
    rows=inputs()
    if args.ids:
        ids = set(map(int,args.ids.split(",")))
        if not ids or not ids.issubset(range(1,101)): parser.error("IDs must be 1–100")
        rows=[r for r in rows if r["id"] in ids]
    seeds=json.loads((ROOT/"input/seeds.json").read_text(encoding="utf-8-sig"))
    started=utc()
    stamp=hashlib.sha256((Path(__file__).read_text()+ (ROOT/"agent/fetch.py").read_text(encoding="utf-8") + json.dumps(seeds) + str(args.pages)).encode()).hexdigest()[:12]
    completed, pending = {},[]
    for row in rows:
        path=args.out/"checkpoints"/f'{row["id"]:03}.json'
        if path.exists() and not args.refresh:
            old=json.loads(path.read_text(encoding="utf-8"))
            if old.get("signature")==stamp and all(old.get(k)==row[k] for k in row):
                completed[row["id"]]=old
                continue
        pending.append(row)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures={pool.submit(research,r,seeds,args.pages,args.refresh):r for r in pending}
        for f in as_completed(futures):
            r=f.result()
            r["signature"]=stamp
            save(args.out/"checkpoints"/f'{r["id"]:03}.json',r)
            completed[r["id"]]=r
            print(f'{r["id"]:3} {r["name"]}: {r["verdict"]} ({len(r["sources"])} pages)',flush=True)
    results=[completed[k] for k in sorted(completed)]
    save(args.out/"first-pass.json",results)
    save(args.out/"run.json",{"started":started,"finished":utc(),"run_signature":stamp,
         "records":len(results),"fresh_records":len(pending),"resumed":len(results)-len(pending),
         "max_pages_per_app":args.pages,"workers":args.workers,"inference":"deterministic",
         "source_status":dict(Counter(p["status"] for r in results for p in r["sources"]))})
if __name__=="__main__":
    main()


