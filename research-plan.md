# Research plan: source-level integrity vs. wire-level pinning for MCP rug pulls

Status as of 2026-09-16. Scoped for a 2-3 day preprint, built on top of Tooldex's
trust-gate feature and grounded in same-session empirical checks (not assumed).

## Research question

Can an MCP tool be silently reprogrammed to do something different, in a way
that's invisible to every integrity check currently used to catch that — which
all inspect only the tool's *declared interface* (name, description, input
schema) as transmitted over the protocol, never its *actual code* — and if so,
how often does that gap matter in real deployments?

Two sub-questions, answered by two different methods (see below):
1. **Does the gap exist, mechanically?** (an experiment, not a count)
2. **How much of the real world does it cover?** (a measurement, in service of
   question 1 — not the headline on its own)

## Why this matters

"MCP rug pull" — a tool's definition or behavior silently changing after a
user/agent already approved it — is an actively studied, named attack class
right now, not a niche concern. Multiple independent, recently-active projects
already build defenses against it: ETDI (cryptographic signing of tool
definitions), MCP-Scan (hash-based tool pinning, in real use), and — most
relevant — **hardened-mcp-server**, **mcpseal**, and **mcp-pin**, all of which
measure or implement wire-level tool-definition pinning.

All three of those closest projects **explicitly name the same blind spot as
their own acknowledged limitation**, unprompted, in their own documentation:

> hardened-mcp-server: launch-command identity binding is "a weaker property
> than hashing executable contents."

> mcpseal: "A malicious server could theoretically modify its actual execution
> logic without changing the declared name, description, or input schema, and
> mcpseal would not detect this."

> mcp-pin: "Day one malice is invisible. This detects *change*... It reports
> that bytes differ" [wire bytes].

That's a strong signal: independent builders converged on recognizing this
exact gap matters, but none of them closed it or measured its real-world
scope. That's the audience and the stakes — not a hypothetical.

## Method

### Part 1 — Demonstrate the gap exists (the actual research contribution)

Not asserted, executed: `scripts/experiment_rug_pull.py` in this repo.

- A minimal MCP server (`echo` tool) is probed twice: once as originally
  written, once after a body-only edit that preserves its name, description,
  and input schema exactly, but changes what it does (leaks `$USER` into the
  response — a stand-in for any schema-preserving malicious behavior change).
- Three signals are compared before/after:
  - **Wire hash** — sha256 of the canonicalized `{name, description,
    inputSchema}`, replicating the strongest policy tested by
    hardened-mcp-server ("pin the raw wire object," their best performer at
    7/8 attacks caught).
  - **File hash** — sha256 of the server script's bytes, what Tooldex's
    `trust_store.py` actually pins.
  - **Real tool output** — an actual `tools/call`, to confirm behavior really
    changed, not just that we assume it did.
- **Result (already run, reproducible):** wire hash identical before/after
  (undetected); file hash different (detected); real output different
  (confirmed genuine behavior change). Confirms the mechanism gap concretely.

Possible extension before writeup: a second mutation variant via an imported
sibling module (mirrors a second real bug found while building Tooldex's
trust gate — multi-file servers where only the entry point was hashed).

### Part 2 — Measure how much the gap matters in practice

File-hash pinning (or any source-level check) only applies when there's a
local file to hash. Most real MCP servers are launched via package managers
(`npx`, `uvx`) with no local file at all — so the natural next question is:
how much of the real world is even theoretically coverable by this class of
fix?

Two independent samples, cross-validated rather than trusting one:

- **Sample A — real committed configs.** 423 server entries scraped from 240
  real `.cursor/mcp.json` / `.claude/mcp.json` / `.vscode/mcp.json` files on
  GitHub (`scripts/gh_classify.py`-equivalent pipeline). Classified by launch
  mechanism. **Result: 13.5% pinnable** (local script), 86.5% not (dominated
  by `npx` at 43.3%).
- **Sample B — MCPZoo-derived.** 21,129 deduplicated server configs extracted
  by mining install-instruction JSON blocks out of 76,630 real MCPZoo
  listings' own `overview` text (`results/mcpzoo_extracted_servers.jsonl`).
  **Result: 27.4% pinnable**, 72.6% not (dominated by `npx` at 35.4%).

The two samples disagree by ~2x, and that disagreement is reported as a
finding, not smoothed over: Sample A reflects what real end users actually
run (skews toward a handful of heavily-used, npx-packaged tools); Sample B
reflects what server authors themselves publish as install instructions
(skews toward smaller individual/custom projects, more of which are local
scripts). Both firmly bound the true figure to a minority — roughly 1-in-7 to
1-in-4 — not a majority.

### Part 3 — Write-up

Structure: (1) motivate via the named rug-pull literature and the
self-acknowledged gap quotes above — this is extending known work, not
ignoring it; (2) the experiment as primary evidence the gap is real and
mechanical; (3) the two-sample measurement, disagreement stated honestly, as
evidence of practical scope; (4) discussion — source-level pinning is a real,
narrow-but-genuine improvement over every current wire-level defense, but the
majority of real-world risk (package-manager-launched servers) needs a
different fix entirely (registry/version-pinning level, not local-file
level) — do not oversell file-hash pinning as a general answer.

Explicit threats to validity to state up front: both samples are
public-repo/public-listing sourced (selection bias vs. private/enterprise
usage); Sample B's extraction is regex-mined documentation text, not verified
against actually-running deployments; MCPZoo's own gated "verified runnable"
subset was not accessible in this timeframe.

## Related work (what this extends, not duplicates)

**Named-attack / defense literature:**
- ETDI — cryptographic signing of tool definitions (arXiv 2506.01333)
- MCP-Scan / Invariant Labs — hash-based tool pinning, production tool
- hardened-mcp-server (jkelly-dev1) — 20 pinning policies vs. 8 rug-pull
  variants, measured detection rates; closest prior work, explicitly
  wire-level only (methodology basis for this project's "wire hash" baseline)
- mcpseal (confuseddude) — wire-level definition pinning, explicit limitation
  quoted above
- mcp-pin (GautamTalksDev / Gautam Bharti) — active, live-crawling wire-level
  fingerprinting project; closest-orbiting active work, worth monitoring —
  findings docs dated as recently as 2026-09-03
- mcp-drift-monitor, mcp-security-inspector, MCP DriftGuard — adjacent
  wire/metadata-level drift tooling, same blind spot

**Taxonomy / measurement literature:**
- MCP-DPT — 6-layer defense-placement taxonomy (arXiv 2604.07551); no cell
  for source-code/executable-level integrity checking; finds existing
  defenses "predominantly tool-centric" with gaps at the host-orchestration
  layer, which is exactly where Tooldex's trust gate sits
- MCP-38 — comprehensive threat taxonomy (arXiv 2603.18063)
- MCPTox — tool-poisoning benchmark, 45 live servers / 353 tools / 1312 attack
  cases (arXiv 2508.14925) — different attack class (malicious instructions
  in descriptions at registration time, not post-approval drift)
- Bharti, "Registry Descriptions Go Stale Unevenly" (arXiv 2608.00997) — 89-day
  measurement of *registry listing* staleness; adjacent temporal-drift problem,
  still wire/metadata-level, not source-code-level
- MCPGuard, MCPThreatHive — protocol-vulnerability and threat-intel focused;
  confirmed via direct read to not touch source-code integrity

**Explicitly ruled out as this project's direction (documented for context,
not reused):**
- MCPZoo itself (arXiv 2512.15144) — the dataset, used here only as a mining
  source for Part 2, Sample B
- Ecosystem redundancy/duplication measurement — already covered by "A
  Measurement Study of MCP Ecosystem" (arXiv 2509.25292) and the near-duplicate
  analysis in "What a Random Draw from the MCP Registry Contains" (arXiv
  2609.10962)
- Cross-client tool-list divergence (VSCode collapse / Copilot CLI
  case-sensitivity bugs) — real bugs, but untestable via Tooldex's own
  discovery layer, which bypasses each client's rendering layer entirely
- Cross-client config drift in public repos — real but too thin a sample
  (~0.5% co-occurrence) to carry a paper on its own

## Open / not yet decided

- Whether to run the second (multi-file import) mutation variant before
  writeup, or ship with the single echo-server demo.
- Whether to attempt the MCPZoo gated "verified runnable" access request in
  parallel (low cost, uncertain/slow payoff — would only upgrade Sample B's
  provenance, not change the core experiment).
