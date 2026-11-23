# Toolkit Atlas

By **Pranav Attarde**

## Problem statement

Which of 100 applications can support an agent-callable toolkit, which need an access agreement, and where would additional engineering duplicate existing coverage?

Fifty-one apps have a documented path to a scoped prototype. Composio already lists 44 of them. Seven merit a closer catalog gap review. Twelve other apps need substantial access approval.

**[Open the live case study](https://pranavattarde.github.io/composio-toolkit-atlas/)** · [Source repository](https://github.com/pranavattarde/composio-toolkit-atlas) · [Research records (JSON)](docs/data/apps.json) · [CSV](docs/data/apps.csv) · [Successful research run](https://github.com/pranavattarde/composio-toolkit-atlas/actions/runs/45240712943)

For the offline edition, extract the complete ZIP and open **START-HERE.html**. The index, charts, app search and evidence notes work locally. Source links open the original websites.

## Run the research agent

Requires Python 3.10 or newer and outbound HTTPS. From the repository root:

```sh
python -m pip install -r requirements.txt
python agent/research.py --ids 27,61,80,90,98
python agent/research.py --ids 80 --refresh
python agent/research.py --workers 6 --out runs/full
```

The first command after installation reproduces the five-app pilot scope. The second forces a single-app recheck. The last runs all 100. Each run directory contains first-pass.json, run.json and individual checkpoints. Repeating the same command resumes compatible completed records. Use --refresh to bypass checkpoints and the one-day page cache. No keys, GPU, paid inference, billing account or Composio account are needed.

Alternatively use **Actions → Recheck public documentation → Run workflow** in a public fork. Select app IDs or enter `all`. The standard Ubuntu runner uploads two result files for one day. A run leaves the committed study unchanged. People without write access can inspect the linked successful run or dispatch in their own fork.

To see a fresh run from a clean extraction of the ZIP, use:

```sh
python agent/research.py --ids 80 --refresh --out runs/manual
```

Open `runs/manual/run.json` and look for one fresh record and current start and finish times. Then open `runs/manual/first-pass.json` and inspect Harvest's source URLs, HTTP statuses, timestamps, cache flags and extracted auth evidence. Repeat with IDs `80,98` and confirm that the fresh results now include Mermaid CLI as well. The raw crawler and the published, reviewed release serve different purposes and may classify an app differently.

## Research design

1. The app directory preserves the original names, ordering and website hints in [the canonical CSV](input/apps.csv). Five pilot seed sets augment the directory. Missing hosts, including the ambiguous Paygent hint, are left for review.
2. The Python runner follows ranked same-vendor links, reads public documentation under robots policy and extracts short pieces of text for access, auth and interface rules. Bounded concurrency, per-host pacing, timeouts, transient retries, cache expiry and resumable checkpoints keep the crawl small. The live full run processed 100 rows and 367 page receipts. The first pass inferred a verdict for seven apps. The remainder went to review.
3. The research layer combines AI-assisted interpretation with public vendor guides, maintainers' repositories and indexed vendor documentation. Each decision is recorded in the attributed [review annotations](review). The deterministic fallback runs without those judgments. The release uses these checked-in annotations to resolve product identity, credential issuance, production gates, access scope and MCP ownership. A new crawl alone cannot independently reproduce interpretive research.
4. [The catalog check](agent/catalog.py) reads Composio's public toolkit and documentation sitemaps and verifies candidate toolkit pages. A published MCP route supports a third-party access claim. A known relay with an MCP-suffixed slug is excluded as independent implementation evidence unless another publisher establishes it. The ambiguous YouTube Transcript catalog name is excluded because its underlying provider was unverified. The agent made no authenticated SDK/MCP calls.
5. [The citation checker](agent/check_sources.py) rechecks reviewed, sampled and catalog URLs. It looks for field-specific evidence in the extracted page text. The publication step removes confirmed 404/410 links, lowers unsupported MCP claims and emits a [review queue](docs/data/issues.json) and [correction history](docs/data/corrections.json). Indexed vendor text can support a qualified claim when a page blocks direct access or returns little readable content.
6. [Reference assertions](verification/reference.json) were sourced separately, then scored against both passes. Fifty-nine checks span 30 apps across all ten categories and all four observed outcomes. The baseline matched 21/59 and the corrected dataset matched 59/59. Most checks test specified facts, with exact scalar labels, named multi-label inclusions, two exclusions and one exact set. The sample informed correction, including the Harvest free-account entitlement. These figures describe the sampled assertions only. The complete-set and exclusion checks overlap some named-method checks. Eight browser-rendered text checks are recorded in [browser observations](verification/browser-observations.json). These are automated browser checks.

A later check on ten additional apps compared 13 claims against the frozen first release. Twelve matched. Discord's command-permission update requires a bearer credential that was missing from the normalized auth labels. After correction, all 13 matched. [Frozen values, corrected values and source links](verification/holdout.json).

The latest audit selected two more apps from each original category, with 20 apps and 41 assertions. The same scoring rules yielded 12/41 for the archived first pass, 39/41 for the frozen reviewed release, and 41/41 after fixing DealCloud's bearer transport and the FanBasis checkout interface type. These scores describe the selected claims. FanBasis's credential eligibility remains unresolved. [Stratified audit with frozen values and source links](docs/data/stratified-audit.json).

## Rebuild the exact published snapshot

```sh
python agent/publish_data.py --snapshot
python agent/render.py
python agent/validate.py
python -m http.server 8000 --directory docs
```

Open http://localhost:8000/ or double-click `docs/index.html`. CSS, JavaScript and the full dataset are embedded. Linked data exports sit beside the page. To regenerate the network inputs using fresh public documentation:

```sh
python agent/research.py --out runs/baseline --workers 8 --refresh
python agent/catalog.py
python agent/check_sources.py --refresh
python agent/publish_data.py
python agent/render.py
python agent/validate.py
```

Review changed claims before releasing a new snapshot. Documentation and catalog availability change. Optional browser checks require `python -m pip install playwright`, `python -m playwright install chromium` and `python agent/browser_verify.py`. An existing local Chromium executable can be supplied with `--executable`.

## Interpret the records

- **Access** is the best-supported initial credential path for the named use case. **Buildability** considers that path and meaningful production restrictions. A free sandbox and partner-gated distribution can coexist. The row notes identify which route applies. Self-hosted tools may support local agent skills.
- **Authentication and interfaces** are multi-label. Bearer describes token presentation and can overlap OAuth2 or an API key. Product-specific supplementary mechanisms appear in the source notes. Empty lists mean unverified or inapplicable as explained in the row.
- **Breadth** estimates resource families, without asserting endpoint counts. Focused covers one workflow family, moderate covers several related families and broad spans multiple families. MCP evidence includes vendor-run data tools and developer-only documentation tools. Check the source observation before treating a server as a substitute for a product API.
- **Confidence** reflects support for auth, access and API. High requires a direct text signal for every declared auth and interface label and the access path in sources attributed to that field. Medium indicates incomplete text corroboration or unconfirmed cost. Low marks unresolved buildability or a missing interface. Text signals assist source review. They do not test production entitlement or MCP behavior.
- **Source coverage** is the number of distinct URLs, with per-source check results alongside notes. The evidence rows have public URLs and original observations. Raw pages, credentials, browser profiles and caches are excluded. Timestamps in receipts are UTC.
- **Reader verification**. The case study links directly to four short checks covering Harvest, Telegram, Mermaid CLI and DealCloud. No personal verification is recorded.

## Files

| Path | Contents |
| --- | --- |
| `input/` | Original 100-app list and five seed sets |
| `agent/` | Crawl, catalog comparison, source checks, rendering and validation |
| `review/`, `review-corrections.json` | Authored, source-attributed annotations and explicit amendments |
| `verification/` | Pilot before/after, scored reference probes and browser observations |
| `docs/data/` | Final CSV/JSON, first pass, receipts, corrections, verification and summary |
| `study/`, `docs/index.html` | Editable presentation and self-contained published page |

The deployment uses the public repository’s `main/docs` publishing source on GitHub Pages.
