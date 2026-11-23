"""Optional rendered-source check. Install Playwright and Chromium separately for this command."""
import argparse
import re
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright, Error
from fetch import ROOT,BOT,policy,save,utc

CHECKS=[
 (3,"https://www.pipedrive.com/en/features/crm-api",r"OAuth 2\.0"),
 (17,"https://help.plain.com/article/does-the-plain-mcp-server-support-api-key-authentication-h7d83qtfdzxo4h49x4oyklwx",r"GraphQL"),
 (27,"https://core.telegram.org/bots",r"BotFather"),
 (35,"https://mailchimp.com/developer/marketing/api-concepts/authentication/",r"OAuth 2"),
 (42,"https://developer.woocommerce.com/docs/apis/rest-api/authentication/",r"HTTP Basic Auth"),
 (61,"https://github.com/github/github-mcp-server",r"GitHub MCP Server"),
 (80,"https://help.getharvest.com/api-v2/authentication-api/authentication/authentication/",r"Personal Access Token"),
 (98,"https://github.com/mermaid-js/mermaid-cli",r"SVG/PNG/PDF"),
]
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--executable",help="Use an existing local Chromium browser")
    args=parser.parse_args()
    observations=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path=args.executable,headless=True)
        for id,url,pattern in CHECKS:
            row=dict(id=id,url=url,pattern=pattern,checked_at=utc(),status="unverified")
            page=browser.new_page(user_agent=BOT+"/1.0 (public documentation verification)")
            try:
                def route_handler(route):
                    if route.request.is_navigation_request() and route.request.frame==page.main_frame:
                        dest=route.request.url
                        u=urlparse(dest)
                        if not u.hostname: return route.abort()
                        rules,problem=policy(u.scheme+"://"+u.netloc)
                        if problem or (rules and not rules.can_fetch(dest,BOT)):
                            return route.abort()
                    return route.continue_()
                page.route("**/*",route_handler)
                response=page.goto(url,wait_until="domcontentloaded",timeout=20000)
                page.get_by_text(re.compile(pattern,re.I)).first.wait_for(state="attached",timeout=4500)
                body=page.locator("body").inner_text(timeout=5000)
                match=re.search(pattern,body,re.I)
                row.update(title=page.title(),status="matched" if match else "missing",http=response.status if response else None)
                if match:
                    row["excerpt"]=re.sub(r"\s+"," ",body[max(0,match.start()-32):match.end()+45]).strip()
            except Error as err:
                row.update(status="not verified",detail=type(err).__name__,title=page.title() if not page.is_closed() else "")
            finally:
                page.close()
            observations.append(row)
            print(id,row["status"],flush=True)
        browser.close()
    save(ROOT/"verification/browser-observations.json",observations)

if __name__=="__main__":
    main()
