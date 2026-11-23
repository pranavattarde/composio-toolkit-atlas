"use strict";
const {apps,summary:s,checks,run,browser,holdout}=JSON.parse(document.querySelector("#dataset").textContent);
const el=(sel)=>document.querySelector(sel);
const E=(value)=>String(value??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const allStates=["READY","CONDITIONAL","GATED","BLOCKED","UNKNOWN"];
const fmt=x=>Array.isArray(x)?x.join(", ")||"Unverified":String(x??"Unverified");
const percent=(hits,total)=>((100*hits/total).toFixed(1)).replace(/\.0$/,"")+"%";
const status=x=>'<span class="status '+x+'"><i class="swatch"></i>'+x+'</span>';
const link=(u,t)=>'<a href="'+E(u)+'" target="_blank" rel="noopener noreferrer">'+E(t)+'</a>';
const openButton=(id,t)=>'<button class="textbtn" data-open="'+id+'">'+E(t)+'</button>';
const hits=s.final_hits,total=s.tested_fields;
const readable=s.readable_sources, sources=s.reviewed_sources;
const shortCat=["CRM & sales","Support & helpdesk","Communications","Marketing & ads","Ecommerce","Data, SEO & scraping","Developer & infra","Productivity","Finance & fintech","AI, research & media"];
el("#headline").textContent=s.verdict.READY;
el("#deck").textContent="Composio already lists "+s.ready_listed+" of those "+s.verdict.READY+". The other "+(s.verdict.READY-s.ready_listed)+" warrant a catalog gap review. For the "+s.verdict.GATED+" gated apps, start with an access sponsor.";
el("#map").innerHTML=apps.map(r=>'<button class="tile '+r.verdict+'" data-open="'+r.id+'" title="'+E(r.name+' · '+r.verdict)+'" aria-label="'+E('Open '+r.name+', '+r.verdict)+'"></button>').join("");
el("#legend").innerHTML=allStates.map(v=>'<span class="key '+v+'"><i class="swatch"></i>'+E(v[0]+v.slice(1).toLowerCase())+' '+(s.verdict[v]||0)+'</span>').join("");
const metrics=[
 [s.selfserve+"/100","Self-serve credential paths","Includes free accounts, trials and self-serve routes with unverified cost. Local installations are counted separately."],
 [s.free_with_restrictions,"Free to start, restricted later","These apps offer a free or trial path and still receive a conditional or gated verdict. Plaid's sandbox uses synthetic data."],
 [s.official_mcp.Verified+"/100","Vendor MCP servers","The scope ranges from docs search to live operations. Mailchimp's documentation server and Shopify's shopper tools serve different workflows."],
 [s.verdict.GATED,"Apps needing an access sponsor","An external approval or enterprise entitlement stands between a prototype and the proposed customer workflow."]
];
el("#metrics").innerHTML=metrics.map(([v,h,p])=>'<div class="metric"><div class="number">'+E(v)+'</div><h3>'+E(h)+'</h3><p>'+E(p)+'</p></div>').join("");
function barRows(obj,max=100){return Object.entries(obj).map(([k,v])=>'<div class="barrow"><span>'+E(k)+'</span><div class="bartrack"><div class="barfill" style="width:'+100*v/max+'%"></div></div><span class="value">'+v+'</span></div>').join("")}
el("#categories").innerHTML=s.categories.map((c,i)=>'<button class="catrow" data-cat="'+E(c.name)+'" title="'+E(Object.entries(c.verdict).map(([a,b])=>a+' '+b).join(', '))+'"><span>'+shortCat[i]+'</span><span class="strip">'+allStates.filter(v=>c.verdict[v]).map(v=>'<i class="'+v+'" style="flex:'+c.verdict[v]+'"></i>').join("")+'</span><span class="value">'+(c.verdict.READY||0)+'/10</span></button>').join("")+'<p class="muted">Right-hand counts show READY apps. Productivity has nine. Finance has two, including sandbox and testnet development paths.</p>';
el("#accesschart").innerHTML=barRows(s.access,100);
const authLeader=Object.entries(s.auth)[0];
const blockerLeader=Object.entries(s.blocker_type).find(([k])=>k!=="None");
el("#patternNote").textContent=authLeader[0]+" is the most common authentication method ("+authLeader[1]+"/100). Plan or payment requirements are the largest primary blocker ("+blockerLeader[1]+" apps). Standardizing OAuth onboarding helps many connectors, but each still needs an entitlement check.";
el("#breakdowns").innerHTML=[["Auth methods",s.auth],["Interface types",s.api],["API breadth",s.surface],["Primary blocker",s.blocker_type],["Public interface evidence",s.remote_api],["MCP ownership",{"Vendor":s.official_mcp.Verified,"Third party":s.third_party_mcp.Verified,"Both":s.both_mcp}]].map(([h,obj])=>'<div><h3>'+h+'</h3>'+barRows(obj)+'</div>').join("");
el("#roadIntro").textContent="Of the "+s.verdict.READY+" ready apps, "+(s.verdict.READY-s.ready_listed)+" had no confirmed match in this catalog scan. These three offer a narrow first tool and a concrete way to evaluate it.";
const road=[
 [16,"LiveAgent","Trial workspace","Test a read-only ticket search against the same agent's native MCP results. Compare ticket visibility across roles before proposing additional tools."],
 [37,"systeme.io","Free account","Try contact lookup by tag. Check the vendor MCP's filtering and pagination before investing in a connector that duplicates it."],
 [42,"WooCommerce","Local test shop","Validate order lookup on a seeded shop. Compare a read-only REST key with the WordPress MCP Adapter on the same order."]
];
el("#roadmap").innerHTML=road.map(([id,n,a,p])=>'<div class="road"><small>'+E(a)+'</small><h3>'+E(n)+'</h3><p>'+E(p)+'</p>'+openButton(id,"View sources")+'</div>').join("");
el("#outreach").innerHTML='<strong>Start vendor conversations in parallel.</strong> '+openButton(90,"PitchBook")+' requires a separate API contract. '+openButton(10,"DealCloud")+' needs a customer tenant and an API-enabled user group. For '+openButton(84,"Paygent Connect")+', first ask the requester to identify the NMI-powered product and its credential issuer.';
const options=(sel,values)=>{for(const value of values){const o=document.createElement("option");o.value=o.textContent=value;el(sel).append(o)}};
options("#category",s.categories.map(c=>c.name)); options("#verdict",allStates); options("#access",Object.keys(s.access));
function body(r){
 const fact=(k,v)=>'<div><dt>'+E(k)+'</dt><dd>'+E(v)+'</dd></div>';
 const notes=r.sources.map(o=>{let h;try{h=new URL(o.url).hostname}catch{h=o.url}
 const reach=o.fetch_status==="readable"?"direct text retrieved":"direct reader: "+o.fetch_status;
 return '<li>'+link(o.url,h)+' <small>· '+E(o.claims.join(", "))+' · '+E(reach)+'</small><br>'+E(o.note)+'</li>'}).join("");
 return '<div class="detailsbody"><p class="description">'+E(r.description)+'</p><p class="muted">'+E(r.category)+' · '+(r.website?link(r.website,"Official site"):"Official site unresolved")+' · Checked '+E(r.last_checked)+' UTC</p><dl class="facts">'+
 fact("Credential access",r.access)+fact("Authentication",fmt(r.auth))+fact("Interfaces",fmt(r.api))+fact("API breadth",r.surface)+fact("Vendor MCP",r.official_mcp)+fact("Third-party MCP",r.third_party_mcp)+fact("Remote API",r.remote_api)+fact("Confidence",r.confidence)+fact("Primary blocker",r.blocker_type)+'</dl><p><strong>Capabilities.</strong> '+E(fmt(r.capabilities))+'</p><p><strong>Developer path.</strong> '+E(r.access_note)+'</p><p><strong>Build decision.</strong> '+E(r.toolkit)+' '+E(r.blocker)+'</p><p><strong>Open questions.</strong> '+E(r.unknowns.join(" ")||"No additional question recorded.")+'</p><p>'+(r.composio_listing?link(r.composio_listing,"Composio catalog match"):"Composio catalog match unconfirmed.")+'</p><strong>Source observations</strong><ol class="sources">'+notes+'</ol></div>'
}
function render(){
 const q=el("#search").value.toLowerCase().trim(),category=el("#category").value,verdict=el("#verdict").value,access=el("#access").value;
 const list=apps.filter(r=>(!category||r.category===category)&&(!verdict||r.verdict===verdict)&&(!access||r.access===access)&&(!q||[r.name,r.id,r.category,r.description,r.blocker,r.toolkit,...r.capabilities,...r.auth,...r.api].join(" ").toLowerCase().includes(q)));
 el("#matches").textContent=list.length+" of "+apps.length+" apps";
 el("#rows").innerHTML=list.length?list.map(r=>'<details class="app" id="app-'+r.id+'"><summary><span class="name"><span class="id">'+String(r.id).padStart(2,"0")+'</span>'+E(r.name)+'</span><span class="accesscell">'+E(r.access)+'</span><span class="apicell">'+E(fmt(r.api))+'</span>'+status(r.verdict)+'</summary></details>').join(""):'<p>No apps match these filters. Change the filters or use Reset.</p>';
 for(const dit of el("#rows").children){if(dit.tagName==="DETAILS")dit.addEventListener("toggle",()=>{if(dit.open&&!dit.querySelector(".detailsbody"))dit.insertAdjacentHTML("beforeend",body(apps[Number(dit.id.slice(4))-1]))})}
}
function clearFilters(){for(const key of ["search","category","verdict","access"])el("#"+key).value=""}
function showApp(id){const current=el("#app-"+id);if(!current){clearFilters();render()}const row=el("#app-"+id);if(!row)return;row.open=true;row.scrollIntoView({block:"start",behavior:"instant"});row.querySelector("summary").focus({preventScroll:true})}
for(const id of ["category","verdict","access"])el("#"+id).addEventListener("change",render);
el("#search").addEventListener("input",render);
el("#reset").addEventListener("click",()=>{clearFilters();render();el("#search").focus()});
document.addEventListener("click",e=>{const b=e.target.closest("[data-open],[data-cat]");if(!b)return;if(b.dataset.open)showApp(Number(b.dataset.open));else{clearFilters();el("#category").value=b.dataset.cat;render();el("#directory").scrollIntoView({block:"start",behavior:"instant"})}});
render();
el("#verificationIntro").textContent=s.tested_apps+" sampled apps span all "+s.sample_categories+" categories and every observed verdict. Each pass was compared with the same "+total+" source-backed assertions.";
el("#score").innerHTML=[[s.first_hits,"Rules-only first pass"],[hits,"After source review"]].map(([v,label])=>'<div><strong>'+percent(v,total)+'</strong><span>'+label+' · '+v+'/'+total+'</span></div>').join("");
el("#rubric").textContent="One point per documented assertion. Scalar labels must match; most multi-label checks test a named method, with explicit exclusions and a complete-set check where stated. Missing answers count as misses. This purposive sample was used during correction, so the final score measures reconciliation on those claims. It does not estimate accuracy across every field.";
el("#holdout").innerHTML='<div class="callout"><strong>Fresh check on a frozen release: '+holdout.frozen_hits+'/'+holdout.total+' matched.</strong> Ten additional apps were checked after the initial release. Discord listed OAuth2 and bot authentication, but omitted the bearer credential on command-permission updates. The source-backed fix brings these checks to '+holdout.published_hits+'/'+holdout.total+'. '+link("https://github.com/pranavattarde/composio-toolkit-atlas/blob/main/verification/holdout.json","Inspect the frozen values and sources")+'</div>';
const lessons=[
 [80,"A legacy method looked current","The pilot flagged Basic auth in Harvest's migration text. The current v2 guide specifies OAuth2 or a personal token. A separate help article confirmed free accounts can use the API."],
 [90,"A blocked fetch hid a real API","PitchBook returned HTTP 403 to the first crawler. Its own help center describes a REST API sold under a separate agreement. The verdict moved from UNKNOWN to GATED."],
 [84,"One identity is still unresolved","A marketing page names Paygent Connect, but it does not establish an NMI affiliation. This row remains UNKNOWN."]
];
el("#mistakes").innerHTML=lessons.map(([id,h,p])=>'<article class="note"><small>'+E(apps[id-1].name)+'</small><h3>'+E(h)+'</h3><p>'+E(p)+'</p>'+openButton(id,"Inspect evidence")+'</article>').join("");
el("#auditLabel").textContent="Inspect all "+total+" scored checks";
el("#auditRows").innerHTML=checks.map(q=>'<details class="audit"><summary>'+E(q.name)+' · '+E(q.field)+' · '+(q.first_correct?"hit":"miss")+' → '+(q.final_correct?"hit":"miss")+'</summary><p>First: '+E(fmt(q.first))+' · Final: '+E(fmt(q.final))+' · Test: '+E(q.operator||(Array.isArray(q.final)?"contains":"equals"))+' '+E(fmt(q.expected))+'</p><p>'+E(q.note)+' '+link(q.url,"Reference")+'</p></details>').join("");
el("#runMeta").textContent="The production snapshot's first pass processed "+run.records+" apps and "+s.first_sources+" page receipts with "+run.workers+" workers. "+browser.filter(r=>r.status==="matched").length+" of "+browser.length+" rendered-browser text checks matched. A workflow rerun produces a downloadable artifact and keeps the published snapshot intact.";
el("#limits").textContent=s.coverage_apps+"/100 apps have cited sources. The direct reader extracted text from "+readable+" of "+sources+" distinct published URLs. Indexed vendor text supports some JavaScript-only or restricted pages. Auth, access and interface sources cover "+s.source_fields.auth+", "+s.source_fields.access+" and "+s.source_fields.api+" apps, respectively. MCP counts are documented lower bounds and include developer-only servers. High confidence requires documented auth, access and API with readable sources. App-level evidence and unresolved questions remain visible above.";
if(/^#app-\d+$/.test(location.hash))showApp(Number(location.hash.slice(5)));
