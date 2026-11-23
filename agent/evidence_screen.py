"""Screen actual page text for each declared label. Matches are triage evidence only."""
import re

PATTERNS = {
 "auth": {
   "OAuth2":r"\boauth(?:[\s-]*2(?:\.0|\.1)?)?\b",
   "API key":r"\b(?:api[ _-]?keys?|x-api-key|secret keys?|consumer key|client[_ ]id.{0,25}(?:secret|password))\b",
   "Bearer token":r"\bbearer\b|\bpersonal access tokens?\b",
   "Basic":r"\bbasic (?:auth|authentication)\b|curl\b.{0,90}?\s(?:-u|--user)\s",
   "Service account":r"\b(?:service (?:account|user)|system user|machine user|workload identity)\b",
   "Other":r"\b(?:jwt|hmac|signature|app token|bot token|bot.{0,22}authentication token|key pair|key-pair|oauth 1|client certificate|mTLS|signed request)\b",
 },
 "api": {
   "REST":r"\brest(?:ful)?\b", "GraphQL":r"\bgraphql\b", "SOAP":r"\bsoap\b",
   "HTTP API":r"\b(?:api endpoint|http api|https api|HTTP-based|GET /|POST /|curl |https://api\.)",
   "gRPC":r"\bgrpc\b", "RPC":r"\b(?:rpc|grpc|json-rpc)\b", "WebSocket":r"\bwebsockets?\b",
   "CLI":r"\b(?:cli|command.line)\b", "SDK":r"\b(?:sdks?|client librar(?:y|ies))\b",
   "Node.js library":r"\bnode\.?js\b",
 },
 "access": {
   "Self-serve free":r"\b(?:free (?:plan|forever|account|tier|developer|edition|sandbox|to use|of charge)|(?:all|every) (?:plans?|accounts?)|no credit card|at no (?:additional )?cost|free and paid|for free|\\$0 per)\b",
   "Self-serve trial":r"\b(?:trial|trialling|trialing|free credits?|testing credit)\b",
   "Self-serve (cost unverified)":r"\b(?:create|generate|register|issue) (?:a |an |your |new )?(?:api key|token|app|integration|personal access token)\b",
   "Paid plan":r"\b(?:paid plans?|paid accounts?|enterprise|business plan|subscription|premium plan|pro plan|professional plan)\b",
   "Partner/sales":r"\b(?:partner|sales team|contact sales|contract|approved|approval|apply for|application review)\b",
   "Admin approval":r"\b(?:admin(?:istrator)?s?|owner|approv(?:al|ed)|user group|access level)\b",
   "Local/open source":r"\b(?:open.source|self.host(?:ed|ing)?|local installation|docker|install locally|npm install|pipx install)\b",
 }
}
PATTERNS={k:{v:re.compile(p,re.I) for v,p in mapping.items()} for k,mapping in PATTERNS.items()}

def page_signals(page):
    if page["status"]!="readable":
        return {}
    text=page["title"]+"\n"+page["text"]
    return {field:[label for label,pattern in choices.items() if pattern.search(text)]
            for field,choices in PATTERNS.items()}

def inspect_app(row,tickets):
    result={}
    for field in PATTERNS:
        labels=row[field] if isinstance(row[field],list) else [row[field]]
        checks=[]
        for label in labels:
            if label not in PATTERNS[field]:
                continue
            source=next((s["url"] for s in row["sources"] if field in s["claims"] and label in
                         tickets.get(s["url"],{}).get("text_signals",{}).get(field,[])),None)
            checks.append({"label":label,"matched_url":source})
        result[field]=checks
    return result

def confidence(row,screen):
    if row["verdict"]=="UNKNOWN" or not row["api"]:
        return "Low"
    if row["access"] in {"Unknown","Self-serve (cost unverified)"}:
        return "Medium"
    for field,checks in screen.items():
        if field=="auth" and not row["auth"] and row["access"]=="Local/open source":
            continue
        if not checks or not all(c["matched_url"] for c in checks):
            return "Medium"
    return "High"
