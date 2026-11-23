"""Polite, bounded reading of public documentation. Cache is local and expires."""
import hashlib
import json
import os
import re
import threading
import time
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urldefrag, urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from protego import Protego

BOT = "ToolkitAtlasResearch"
HEADERS = {"User-Agent": BOT + "/1.0 (public documentation research; https://github.com/pranavattarde/composio-toolkit-atlas)"}
ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / ".cache"
CACHE.mkdir(exist_ok=True)
LIMIT = 2_500_000
TTL = 86400
locks = defaultdict(threading.RLock)
rules = {}
last = {}
local = threading.local()

def utc():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def save(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)

def valid(url):
    p = urlparse(url)
    return p.scheme in {"https","http"} and p.hostname and "." in p.hostname and not p.username and not p.password

def request(url, cap=LIMIT):
    if not hasattr(local, "session"):
        local.session = requests.Session()
        local.session.headers.update(HEADERS)
    for attempt in range(3):
        try:
            with local.session.get(url, timeout=(5,10), stream=True, allow_redirects=False) as r:
                if r.status_code in {429, 502, 503, 504} and attempt < 2:
                    retry = r.headers.get("Retry-After")
                    if retry and (not retry.isdigit() or int(retry) > 12):
                        return r.status_code, "", dict(r.headers)
                    time.sleep(max(2 ** attempt, int(retry or 0)))
                    continue
                data = bytearray()
                for chunk in r.iter_content(32768):
                    data.extend(chunk)
                    if len(data) >= cap:
                        break
                encoding = r.encoding if r.encoding and r.encoding.lower() != "iso-8859-1" else "utf-8"
                return r.status_code, data[:cap].decode(encoding, errors="replace"), r.headers.copy()
        except (requests.RequestException, OSError) as e:
            if attempt == 2:
                return 0, "", {"error": type(e).__name__}
            time.sleep(2 ** attempt)
    return 0, "", {}

def policy(origin):
    if origin not in rules:
        path = origin + "/robots.txt"
        for _ in range(4):
            status, body, headers = request(path, 512000)
            if 300 <= status < 400 and headers.get("Location"):
                path = urljoin(path, headers["Location"])
                if not valid(path):
                    break
                continue
            break
        if status in {404, 410}:
            rules[origin] = (None, "")
        elif status == 200:
            rules[origin] = (Protego.parse(body), "")
        else:
            rules[origin] = (None, f"robots_http_{status}")
    return rules[origin]

def extract(html, url, kind):
    if "html" not in kind.lower() and not re.search(r"<(?:html|body|main|article|!doctype)", html[:2000], re.I):
        return "", re.sub(r"\s+", " ", html)[:100000], []
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    links = []
    for a in soup.select("a[href]"):
        dest = urldefrag(urljoin(url, a.get("href","")))[0]
        label = " ".join(a.stripped_strings)[:110]
        if label and valid(dest) and dest not in {x[1] for x in links[-8:]}:
            links.append([label,dest])
    for x in soup.select("nav,script,style,footer,header,aside,svg,noscript,[aria-hidden=true]"):
        x.decompose()
    main = soup.select_one("article.markdown-body") or soup.find("main") or soup.find("article") or soup
    return title, re.sub(r"\s+", " ", main.get_text(" ", strip=True))[:140000], links[:1800]

def fetch(url, refresh=False):
    key = hashlib.sha256(url.encode()).hexdigest()
    path = CACHE / (key + ".json")
    with locks["url:" + url]:
        if not refresh and path.exists() and time.time()-path.stat().st_mtime < TTL:
            page = json.loads(path.read_text(encoding="utf-8"))
            page["cached"] = True
            return page
        page = dict(url=url, final_url=url, checked_at=utc(), status="invalid_url", http=0, title="", text="", links=[], cached=False)
        current = url
        for _ in range(6):
            if not valid(current):
                break
            parsed = urlparse(current)
            origin = parsed.scheme + "://" + parsed.netloc
            with locks["host:" + origin]:
                rule, problem = policy(origin)
                if problem or (rule and not rule.can_fetch(current, BOT)):
                    page.update(status=problem or "robots_disallowed",final_url=current)
                    break
                delay = max(0.45, (rule.crawl_delay(BOT) if rule else 0) or 0)
                if delay > 30:
                    page.update(status="crawl_delay_deferred")
                    break
                time.sleep(max(0, last.get(origin,0)+delay-time.monotonic()))
                code, body, headers = request(current)
                last[origin] = time.monotonic()
            page.update(http=code,final_url=current)
            if 300 <= code < 400 and headers.get("Location"):
                current = urljoin(current,headers["Location"])
                continue
            if code != 200:
                page["status"] = "http_" + str(code) if code else headers.get("error","network_error")
                break
            kind = headers.get("Content-Type","")
            if not any(x in kind.lower() for x in ("text/", "json", "xml", "markdown", "yaml", "octet-stream")):
                page["status"] = "unsupported_media"
                break
            title, content, links = extract(body,current,kind)
            page.update(title=title,text=content,links=links,status="readable" if len(content)>=100 else "thin")
            if re.search(r"just a moment|access denied|security checkpoint|page not found|404 not found",title,re.I):
                page.update(status="challenge_or_missing",text="",links=[])
            break
        save(path,page)
        return page

def receipt(page):
    return {k:page[k] for k in ("url","final_url","status","http","title","checked_at","cached")}

