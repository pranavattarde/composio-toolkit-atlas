"""Match the canonical names against Composio's own public sitemap, then check each page."""
import re
import time
from pathlib import Path
from urllib.parse import urlparse

from fetch import ROOT, BOT, fetch, last, locks, policy, receipt, request, save, utc
from research import inputs

SITEMAP = "https://composio.dev/toolkits/sitemap.xml"
ALIASES = {7:["zohocrm","zoho"],23:["zohocliq"],24:["lark","larksuite"],28:["whatsapp"],32:["metaads","facebookads"],34:["highlevel","gohighlevel"],37:["systemeio"],39:["threads"],45:["adobecommerce","magento"],49:["amazonsellingpartner","amazonsellingpartnerapi"],63:["netlifymcp"],68:["mongodb"],69:["datadog"],76:["monday"],83:["binance"],92:["otterai","otter","otteraimcp"],96:["devinmcp"],97:["higgsfieldai"],99:["transcriptapi"]}
def norm(name):
    return re.sub(r"[^a-z0-9]","",name.casefold())

def run():
    origin="https://composio.dev"
    rules,error=policy(origin)
    if error or (rules and not rules.can_fetch(SITEMAP,BOT)):
        raise RuntimeError("Catalog sitemap unavailable under the site's crawl policy")
    time.sleep(max(0.5,(rules.crawl_delay(BOT) if rules else 0) or 0))
    status,body,_=request(SITEMAP)
    if status!=200 or "</urlset>" not in body:
        raise RuntimeError("Catalog sitemap unavailable or truncated")
    urls = re.findall(r"<loc>(https://composio\.dev/toolkits/[^/<]+)</loc>",body)
    lookup={norm(u.rsplit("/",1)[1]):u for u in urls}
    result=[]
    for app in inputs():
        names=[norm(app["name"])]+ALIASES.get(app["id"],[])
        url=next((lookup[n] for n in names if n in lookup),None)
        # The name matches another transcript connector; its upstream provider is unspecified.
        if app["id"] == 99:
            url = None
        row={"id":app["id"],"catalog_route":None,"mcp_route":False}
        if url:
            page=fetch(url)
            note=receipt(page)
            if page["status"]=="readable":
                row["catalog_route"]=url
                row["mcp_route"]=bool(re.search(r"\bMCP server\b",page["title"]+" "+page["text"][:350],re.I))
                row["title"]=page["title"]
            row["receipt"]=note
        result.append(row)
    save(ROOT/"runs/catalog.json",{"checked_at":utc(),"sitemap":SITEMAP,"links_scanned":len(urls),"matches":result})
    print("Catalog links",len(urls),"matches",sum(bool(x["catalog_route"]) for x in result),"MCP",sum(x["mcp_route"] for x in result))
if __name__=="__main__":
    run()


