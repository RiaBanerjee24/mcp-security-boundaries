# Progress report — rug-pull integrity research

Status as of 2026-09-16, end of a single long working session. Picks up from
`Tooldex/claude/trust-gate-summary.md` (the Tooldex trust-gate feature that
motivated this). Everything below is verified, not assumed — this doc exists
so a fresh session doesn't have to re-derive or re-litigate any of it.

## The research question (final wording, don't re-negotiate this)

Can an MCP tool be silently reprogrammed to do something different, in a way
that's invisible to every integrity check currently used to catch that (which
all inspect only the tool's declared interface — name, description, input
schema — as transmitted over the protocol, never its actual code) — and if
so, how often does that gap matter in real deployments?

Two parts, don't conflate them:
1. **Does the gap exist, mechanically?** — an experiment (done, see below).
2. **How much of the real world does it cover?** — a measurement, in service
   of #1, not a headline on its own (a bare percentage is not a research
   question — this was explicitly corrected mid-session, see "Corrections"
   below).

Full detail, related work, and method: `../research-plan.md`. Read that
file too — this progress report is the "what's actually done + what's next"
companion, not a replacement for it.

## What's done and verified

### 1. Novelty check (thorough, don't redo unless >1 week has passed)

Checked academic literature (ETDI, MCP-DPT, MCPGuard, MCPThreatHive, MCP-38,
MCPTox, "MCP at First Glance", Bharti's registry-drift study) and the live
tool ecosystem (MCP-Scan, hardened-mcp-server, mcpseal, mcp-pin,
mcp-drift-monitor, mcp-security-inspector, MCP DriftGuard).

**Result: no collision, and the evidence is unusually strong.** Three of the
closest, most recently-active projects explicitly name this exact gap as
their own acknowledged limitation, unprompted, in their own docs:

- hardened-mcp-server: launch-command binding is "a weaker property than
  hashing executable contents."
- mcpseal: "A malicious server could theoretically modify its actual
  execution logic without changing the declared name, description, or input
  schema, and mcpseal would not detect this."
- mcp-pin: "Day one malice is invisible. This detects change... It reports
  that bytes differ" [wire bytes only].

**Watch this one**: mcp-pin (GautamTalksDev / Gautam Bharti) has live
crawling infra and findings dated as recently as 2026-09-03 — closest-orbiting
active work. Re-check before publishing that they haven't extended into
source-level checking in the meantime.

### 2. The experiment — proves the gap is real, not asserted

`mock_servers/echo_server.py` + `scripts/experiment_rug_pull.py`. Run it:

```
cd Tooldex-research
uv run --no-project --python 3.14 --with mcp python3 scripts/experiment_rug_pull.py
```

Method: a minimal `echo` tool, probed before and after a body-only edit that
preserves name/description/schema exactly but changes behavior (appends
`$USER` to the response — silent exfil stand-in). Compares wire hash
(replicates hardened-mcp-server's best-performing policy: sha256 of
canonicalized `{name, description, inputSchema}`) vs. file hash (what
Tooldex's `trust_store.py` actually pins) vs. real tool output.

**Actual result from the last run (reproducible):**
```
v1 wire hash: a106160309d014fa20c1af3cffcc508933e08578db3a4a5cbaf37ff5bf009e68
v2 wire hash: a106160309d014fa20c1af3cffcc508933e08578db3a4a5cbaf37ff5bf009e68  <- UNCHANGED
v1 file hash: 8f831f7c05511dd115dac2d4e0097a3dd38ed2255ff08644ef7bb20dee2c1520
v2 file hash: c63dd65062059591d2f2d09d1c012d93b9229eb9075b9fa12b3c5e0d00abb1e7  <- CHANGED
v1 output: 'hello'
v2 output: 'hello | riabanerjee'  <- CHANGED (real leak, not simulated)
```
Wire-level hash misses it. File hash catches it. Confirmed.

The script self-restores `echo_server.py` to v1 at the end — it's safe to
rerun as many times as needed.

### 3. Real-world scope — two independent measurements, cross-validated

**Sample A** (not currently saved as a file — was ad-hoc, rerun via GitHub
Search API if needed): 423 real server entries scraped from 240 actual
`.cursor/mcp.json` / `.claude/mcp.json` / `.vscode/mcp.json` files on GitHub.
**13.5% pinnable** (local script), 86.5% not (43.3% alone is `npx`).

**Sample B** (`results/mcpzoo_extracted_servers.jsonl`, 21,129 deduplicated
entries): extracted by regex-mining `mcpServers` JSON blocks straight out of
76,630 real MCPZoo listings' own `overview` text
(`mcp_servers_all.json` — **gitignored, 432MB, local-only, NOT in the GitHub
repo** — still on disk in `Tooldex-research/` unless deleted). **27.4%
pinnable**, 72.6% not (35.4% alone is `npx`).

**The two samples disagree by ~2x — report this honestly as a finding, not
noise.** Sample A = what real end users actually run (skews toward a handful
of heavily-used npx-packaged tools). Sample B = what server authors
self-publish as install docs (skews toward smaller custom local-script
projects). Both bound the true figure to a clear minority: ~1-in-7 to
~1-in-4, never a majority.

**Important, easy-to-get-backwards distinction (this was corrected
mid-session, don't reintroduce the error):** this percentage is NOT "where
rug pulls happen." It's "where our specific defense (file-hash pinning) is
even capable of reaching." The npx/uvx majority is arguably *more* exposed
in practice (real incident: "Clinejection," a malicious npm package version
live for 8 hours, Feb 2026) — file-hash pinning does nothing for that
majority; it needs a different fix (registry/version pinning), out of scope
here.

### 4. Repo state

- Git repo initialized, pushed to **https://github.com/RiaBanerjee24/TDX-research**
  (private), branch `main`.
- `mcp_servers_all.json` (432MB) is gitignored — exceeds GitHub's 100MB
  file limit, stays local-only.
- Commit author is auto-configured (`Ria Banerjee
  <riabanerjee@Rias-MacBook-Air.local>`) — cosmetic, fine to leave or fix
  with `git config --global user.email` later.
- `Tooldex-research/` was cleaned of all artifacts from the abandoned
  cross-client divergence pilot (see "Explicitly ruled out" below) — nothing
  dead left in the repo.

## What's next (in progress, not finished)

**Extending the demo to real reference servers, not just the toy echo
server** — was mid-execution when the session ended. Goal: same
wire-hash-vs-file-hash mutation test, applied by hand (not automated at
scale — see "Explicitly ruled out") to 3-4 real, popular, actually-deployed
servers, to (a) show the gap isn't an artifact of one contrived example, and
(b) make it concretely demonstrable as "here's what Tooldex's approach
catches on real code."

- Cloned `https://github.com/modelcontextprotocol/servers` (official MCP
  reference implementations) to `/tmp/mcp-refservers/servers` — **this is in
  /tmp, not persisted in Tooldex-research, may not survive a reboot — reclone
  if it's gone:**
  ```
  git clone --depth 1 https://github.com/modelcontextprotocol/servers.git
  ```
- Candidates inspected: `fetch` (Python), `git` (Python), `time` (Python),
  `filesystem` (TypeScript) — good language diversity for generalizing past
  one SDK.
- **Mutation target already identified, not yet executed**: `time` server,
  `TimeServer.get_current_time()` in
  `servers/src/time/src/mcp_server_time/server.py` (method starts line 61) —
  clean, isolated, pure-logic method, fully separate from the `list_tools()`
  schema definition (line 128) so a body-only edit is easy to keep
  interface-preserving. Same pattern as the echo demo: change what's
  `return`ed, keep the docstring/signature identical.
- Not yet started: `fetch` and `filesystem` equivalents.
- After 3-4 of these are done: fold results into `research-plan.md` Part 1
  as additional evidence, then move to the actual writeup (Part 3 of the
  plan).

## Explicitly ruled out this session (don't re-propose without new
information)

- **MCPZoo-based duplicate/redundancy detection** — crowded. Two existing
  papers already measure this quantitatively at larger scale (arXiv
  2509.25292, arXiv 2609.10962).
- **Cross-client tool-list divergence** (VSCode tool-collapse bug, Copilot
  CLI case-sensitivity bug) — real bugs, but Tooldex's own discovery/probe
  layer bypasses each client's actual rendering logic, so it structurally
  cannot observe the phenomenon. Would need instrumentation inside each
  client's own introspection surface (`claude mcp list`, `cursor-agent mcp
  list`, `codex mcp list` — no equivalent for VSCode or Copilot CLI). A pilot
  was actually built and run for this before the flaw was caught — see git
  history / this doc's honesty about wasted time if picking this back up is
  ever considered. Do not resurrect without solving the instrumentation
  problem first.
- **Cross-client config drift in public repos** (do committed `.cursor/`
  `.claude/` `.vscode/` configs in the same repo agree with each other) —
  real, under-studied angle, but too thin a sample: only 18/3,619 repos in a
  real GitHub-search check had 2+ client configs (~0.5%), likely a genuine
  ceiling not a sampling artifact (most multi-client usage is private/closed,
  as originally suspected before checking).
- **Testing Tooldex's own trust_store.py code for robustness/false-positives
  at scale** — explicitly rejected by the user as not the point; this project
  is about the research claim, not validating Tooldex's implementation.
- **Automated mutation testing across a large/unbounded corpus of scraped
  real servers** — rejected as not safely automatable: no generic way to
  make an interface-preserving body edit on arbitrary unknown code across
  languages without real risk of silently breaking the test's validity. The
  bounded hand-done version (3-4 real reference servers) replaces this.

## Corrections made mid-session (context for why things are worded the way
they are)

- A bare percentage ("X% pinnable") is not a research question on its own —
  it's evidence in service of the mechanism claim (the experiment), not the
  headline. Keep this hierarchy in the writeup.
- The pinnable percentage describes defense *coverage*, not attack
  *likelihood* — the npx/uvx majority is plausibly where more real attacks
  land, not fewer. Don't let the writeup imply otherwise.

## Loose ends / things to double check tomorrow

- Revoke the GitHub PAT that was used for the earlier code-search research
  (`ghp_CPbCW8...`, shared in-chat) if that hasn't already been done — it
  was never wired into git credentials, only used for direct API calls, but
  it was exposed in this conversation log regardless.
- Decide whether to pursue MCPZoo's gated "verified runnable" institutional
  access in parallel — low cost, uncertain/slow payoff, would only upgrade
  Sample B's provenance, doesn't change the core experiment either way.
- Once the 3-4 reference-server mutations are done, re-run the novelty check
  on mcp-pin specifically (the fastest-moving adjacent project) before
  finalizing the writeup.
