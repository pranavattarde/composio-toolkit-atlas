"""Match app identities against both public Composio catalogs and check each candidate."""
import re
import time
from urllib.parse import urlsplit

from fetch import ROOT, BOT, fetch, policy, receipt, request, save, utc
from research import inputs

SITEMAPS = ["https://composio.dev/toolkits/sitemap.xml","https://docs.composio.dev/sitemap.xml"]
ALIASES = {
    7:["zohocrm","zoho"],15:["pylonmcp"],23:["zohocliq"],24:["lark","larksuite"],
    28:["whatsapp"],32:["metaads","facebookads"],34:["highlevel","gohighlevel","highlevelagency"],
    37:["systemeio"],39:["threads"],45:["adobecommerce","magento"],49:["amazonsellingpartner","amazonsellingpartnerapi"],
    63:["netlifymcp"],68:["mongodb"],76:["monday"],92:["otterai","otter","otteraimcp"],
    96:["devinmcp"],97:["higgsfieldai"],99:["transcriptapi"]
}
def norm(name):
    return re.sub(r"[^a-z0-9]","",name.casefold())

def sitemap_urls(url):
    u=urlsplit(url)
    rules,error=policy(u.scheme+"://"+u.netloc)
    if error or (rules and not rules.can_fetch(url,BOT)):
        raise RuntimeError("Catalog sitemap unavailable under the site's crawl policy")
    time.sleep(max(0.5,(rules.crawl_delay(BOT) if rules else 0) or 0))
    status,body,_=request(url)
    if status!=200 or "</urlset>" not in body:
        raise RuntimeError("Catalog sitemap unavailable or truncated")
    return re.findall(r"<loc>(https://(?:docs\.)?composio\.dev/toolkits/[^/<]+)</loc>",body)

def run():
    urls=[u for s in SITEMAPS for u in sitemap_urls(s)]
    by_slug={}
    for url in urls:
        by_slug.setdefault(norm(url.rsplit("/",1)[1]),[]).append(url)
    result=[]
    for app in inputs():
        names=[norm(app["name"])]+ALIASES.get(app["id"],[])
        if app["id"]==99:
            names=["transcriptapi"]  # Generic YouTube caption tools have an unspecified upstream provider.
        row={"id":app["id"],"catalog_route":None,"mcp_route":False}
        candidates=list(dict.fromkeys(u for name in names for u in by_slug.get(name,[])))
        for url in candidates:
            page=fetch(url)
            row["receipt"]=receipt(page)
            if page["status"]!="readable":
                continue
            row.update(catalog_route=url,title=page["title"])
            row["mcp_route"]=bool(re.search(r"\bMCP server\b",page["title"]+" "+page["text"][:350],re.I))
            break
        result.append(row)
    save(ROOT/"runs/catalog.json",{"checked_at":utc(),"sitemaps":SITEMAPS,"links_scanned":len(urls),"matches":result})
    print("Catalog links",len(urls),"matches",sum(bool(x["catalog_route"]) for x in result))
if __name__=="__main__":run()
