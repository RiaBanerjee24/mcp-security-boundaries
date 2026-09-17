# Progress report — MCP tool integrity gap research

Status as of 2026-09-17, end of the second working session. **This session
substantially pivoted the project.** Read this whole file before touching
`research-plan.md` or `preprint-frame.md` — both are now partially stale
(see "File status" at the bottom) and this file is the current source of
truth.

## The research question (current, final wording — supersedes prior sessions)

Every current MCP "rug-pull" defense hashes or signs some subset of a
tool's *declared interface* (name, description, schema), never its
implementation. That specific gap is already known/self-acknowledged by
several tools — proving it exists again is not the contribution. What
hasn't been done: (1) a **precise, field-by-field audit** of exactly what
every real, currently-deployed defense actually covers and exactly where
each one stops, and (2) showing that **even the best of them — full
source-file hashing — has its own further boundary**: it covers the
entry-point file only, not what that file imports. The contribution is
locating both boundaries with precision nobody else has, and closing the
second one with a minimal, working reference fix (a whole-dependency-
closure hash), not just describing it.

Two nested claims, not one:
- **Gap 1** (interface vs. implementation): proven, done, reproducible.
- **Gap 2** (entry-point-only vs. dependency closure): structured, not yet
  run — this is the one remaining piece of real work.

## What's done and verified

### 1. The preprint draft exists: `preprint.md` (repo root)

Full draft written this session. Structure: intro + explicit terminology
scoping (§1.1 — "rug pull" means *interface-preserving implementation
change*, explicitly distinguished from two other things the industry calls
"rug pull," see below) → threat model (§2) → the field-level audit table
(§3, fully populated) → Experiment 1/Gap 1 results (§4, fully populated,
real data) → Experiment 2/Gap 2 structure (§5, **marked TODO, not yet
run**) → discussion/limitations/conclusion (scaffolded with TODOs for
things that need your judgment, not more research).

**The single most important remaining task is finishing §5**: run the
import-mutation variant (mutate a module the entry point imports, not the
entry point itself) and show (a) wire hash unchanged, (b) entry-point-only
file hash unchanged (the point — Tooldex's current approach misses this),
(c) a whole-closure hash (`sha256(sorted(sha256(f) for f in [entry_point]
+ resolved_local_imports))`) changed, (d) real output changed. Everything
else in the draft is either finished or is a writing/judgment task for the
user, not a research task.

### 2. Experiment 1 (Gap 1) — unchanged from prior session, still valid

`mock_servers/echo_server.py` + `scripts/experiment_rug_pull.py`. Real,
reproducible result:
```
v1 wire hash: a106160309d014fa20c1af3cffcc508933e08578db3a4a5cbaf37ff5bf009e68
v2 wire hash: a106160309d014fa20c1af3cffcc508933e08578db3a4a5cbaf37ff5bf009e68  <- UNCHANGED
v1 file hash: 8f831f7c05511dd115dac2d4e0097a3dd38ed2255ff08644ef7bb20dee2c1520
v2 file hash: c63dd65062059591d2f2d09d1c012d93b9229eb9075b9fa12b3c5e0d00abb1e7  <- CHANGED
v1 output: 'hello'
v2 output: 'hello | riabanerjee'  <- CHANGED (real leak, not simulated)
```
Rerun: `cd Tooldex-research && uv run --no-project --python 3.14 --with mcp python3 scripts/experiment_rug_pull.py`
Script self-restores v1 at the end; safe to rerun.

### 3. The field-level audit table (`preprint.md` §3) — new this session, the core related-work contribution

Every row was verified by reading the primary source directly this
session (not paraphrased from a secondary summary):

| Defense | Covers | Stops at |
|---|---|---|
| ETDI (arXiv 2506.01333) | name, description, schema, permissions, optional hash of backend *API contract* (OpenAPI/Swagger) | the API contract, not backend code — read the exact quote below |
| mcpseal | name, description, schema | self-acknowledged limitation |
| hardened-mcp-server | raw wire object, best of 20 policies | self-acknowledged limitation |
| mcp-pin / Plumbline | name, description, schema, annotations (RFC 8785) | confirmed via its own 2026-09-03 finding doc — still metadata-only |
| Vercel AI SDK `detectToolDrift` (`ai@7.0.19`, shipped July 2026) | description, resolved schema, title | metadata-only, shipped mainstream SDK feature with the same blind spot |
| MCP Manager (mcpmanager.ai) Feature Governance | name, title, description | confirmed directly from their docs — no schema, no implementation |
| Microsoft APM (`microsoft.github.io/apm`, `github.com/microsoft/apm`) | full content hash of declared agent-context packages, via lockfile | **install-time only**; `apm audit` is manual/opt-in and diffs local hand-edits vs. the lockfile, not upstream changes; different artifact class (agent-context packages, not a live MCP server at the moment of tool invocation) |
| Tooldex `trust_store.py` | full byte content of entry-point file | entry point only — does not follow imports (this is Gap 2) |

**Key new-this-session finding on ETDI**, worth having verbatim since it's
a strong citation: ETDI's own PDF (§ "Preventing Rug Pulls") says *"if the
tool definition includes a hash of its backend API contract (e.g., derived
from an OpenAPI/Swagger specification), any change to this contract by the
tool provider... would alter the hash."* This is still interface-level (an
OpenAPI contract describes what an API promises, not what its backend code
does) and is conditional on the tool having a documented REST contract at
all — most local script-based servers have none. Also checked ETDI's own
"Scenario 2: Silent Modification" sequence diagram: it detects tampering
by someone who does **not** hold the legitimate signing key (a third-party
impersonation/tamper case); it does **not** detect the legitimate
key-holder (the actual rug-pull threat actor) re-signing new content under
an unchanged version label, and it structurally cannot see a
schema-preserving code change at all, regardless of who does it.

### 4. Terminology scoping — "rug pull" is used inconsistently industry-wide, confirmed this session

Checked directly, not assumed:
- **Microsoft's Zero Trust catalog**, ["Rug-Pull Attack (Agent / MCP
  Server)"](https://learn.microsoft.com/en-us/security/zero-trust/catalog-ai-attack-techniques/rug-pull-attack)
  (dated July 2026) — uses "rug pull" for **agent-to-agent** prompt
  injection via a compromised/impersonating peer agent in a multi-agent
  directory. Different mechanism entirely; mitigations offered are all
  org/policy-level (RBAC, DLP, SIEM), nothing about interface-vs-code
  hashing.
- **Pillar Security's report on `google/adk-python`** — a CI/CD
  privilege-escalation / confused-deputy bug (a low-privilege triage bot
  manipulated into triggering a high-privilege maintainer-only workflow).
  Unrelated to tool interface integrity; Google's ADK itself (checked) has
  no built-in tool/agent integrity verification of any kind.

`preprint.md` §1.1 explicitly scopes the paper's usage to avoid being
read as claiming to address either of these.

### 5. Novelty re-checked today, nothing collides

Re-verified live (not from memory) that none of the following do
source-code-level integrity checking: mcp-pin's 2026-09-03 finding,
Plumbline, Vercel's `detectToolDrift`, MCP Manager, Microsoft APM (close,
but install-time-only and a different artifact class), Microsoft's Zero
Trust catalog page (awareness/policy only, no mechanism). See "Prior
novelty check" in the 2026-09-16 section below for the original literature
pass (ETDI, MCP-38, MCPTox, MCPGuard, MCPThreatHive, MCP-DPT, etc.) — still
valid, not re-litigated today.

## What's next (in order)

1. **Run Experiment 2 / Gap 2** (§5 of `preprint.md`) — the one real
   remaining research task. Decide toy (split echo into two files) vs.
   real-server variant (find a reference server whose logic already lives
   in an imported module) — toy is faster and sufficient given the 4-day,
   solo constraint; real-server is stronger if time allows. Either way,
   produce the four-signal table (wire hash / entry-point file hash /
   whole-closure hash / output) and paste it into §5.
2. Write the abstract and conclusion (§Abstract, §8) — deliberately left
   for last, per standard practice, and marked TODO in the draft.
3. Decide whether to keep or cut `preprint.md` §6.3 (the paragraph
   explaining why the population-measurement direction was dropped) —
   recommended to keep, short, as already drafted.
4. Fill remaining citation TODOs in `preprint.md` References (exact repo
   URLs for hardened-mcp-server and mcpseal; Clinejection incident
   source).

## Explicitly ruled out this session (don't re-propose without new information)

- **The 13-27% "pinnable servers" coverage measurement** (Sample A/B from
  the 2026-09-16 session) — not wrong, but demoted out of the headline
  contribution. Reasons: (a) repeated risk of the finding being
  mis-stated as "attacks eliminated" rather than "structural reachability"
  — this happened three separate times in conversation despite correction;
  (b) the methodology (two convenience samples) is weaker than the genre's
  actual exemplars (see next item) — user's own assessment, confirmed
  fair on inspection.
- **General dependency pinning-vs-floating benchmark** (either narrowed to
  MCP or general) — checked live, heavily crowded: ["A Large Scale
  Analysis of Semantic Versioning in
  NPM"](https://arxiv.org/abs/2304.00394) (arXiv 2304.00394, full npm
  registry, time-traveling dependency resolver) and ["Which Is Better For
  Reducing Outdated and Vulnerable Dependencies: Pinning or
  Floating?"](https://arxiv.org/abs/2510.08609) (arXiv 2510.08609,
  survival analysis, npm/PyPI/Cargo) already own this territory at a scale
  no solo 4-day effort can approach.
- **"Pinning is the fix" as a framing** — directly cautioned against by
  ["Pinning Is Futile: You Need More Than Local Dependency Versioning to
  Defend against Supply Chain Attacks"](https://arxiv.org/pdf/2502.06662)
  (arXiv 2502.06662, CMU, FSE'25) — pinning doesn't stop a package that
  was already malicious before you pinned it, doesn't cover transitive
  deps by itself, doesn't stop build-time injection. Engaged with in
  `preprint.md` §6.3 rather than ignored.
- **An MCP-ecosystem drift census of our own** — ruled out hard by
  discovering **["Same Name, Different Server: A Security Census of
  Silent Drift in the MCP
  Ecosystem"](https://arxiv.org/html/2609.14119)** (arXiv 2609.14119).
  This is the most important new find of the session: a full registry
  census (21,643 servers, source fetched for 14,353, an 8-class scanner
  validated against 414 hand-labeled findings; findings: 51.1% of
  multi-version servers changed their advertised interface across
  versions, 40.6% silently). Far larger/more rigorous than anything a
  solo 4-day effort can compete with. **But its own stated limitation is
  the opening this project uses**: *"the registry does not version tool
  definitions, so a behavioural change is invisible in registry data by
  construction."* Even this, the most rigorous MCP census that exists,
  cannot see Gap 1 or Gap 2. `preprint.md` §6.3 positions this project as
  a small, hand-verified complement to that paper's explicitly-named
  blind spot, not a competing population estimate.
- **Generic literature survey + proposal, no implementation** — considered
  and rejected. Two reasons: (a) a general MCP-security SoK already exists
  (arXiv 2512.08290), so a broad survey would need heavy differentiation;
  (b) more fundamentally, a proposal with zero working implementation is
  *weaker* evidence in this field than a small working demo — the opposite
  of what "sharp and concrete" (the user's explicit bar) requires. The
  field-level audit table (kept) is the sharp, differentiated version of
  "survey"; it's paired with working code (Experiment 1, and Experiment 2
  once run), not left as prose alone.
- **The 3-4 real-reference-server mutation extension** (time/fetch/
  filesystem from `modelcontextprotocol/servers`) — superseded, not
  actively pursued right now. This was the plan going into this session;
  it's not wrong, just not the current critical path. Could still be a
  "extended validation" addendum later if time allows after Gap 2 is done,
  but is not required for the current draft.
- *(Carried over from 2026-09-16, still valid, not re-litigated):*
  MCPZoo-based duplicate/redundancy detection (crowded, two existing
  papers); cross-client tool-list divergence (Tooldex's probe layer can't
  observe it); cross-client config drift in public repos (too thin a
  sample, ~0.5%); testing Tooldex's own `trust_store.py` for
  robustness/false-positives (explicitly not the point, per the user);
  automated mutation testing at unbounded scale (not safely automatable
  across arbitrary code).

## Corrections made this session (context for why things are worded the way they are — watch for these recurring)

- **"Coverage" vs. "elimination"/"effectiveness" got conflated three
  separate times** in conversation (once about the original 13-27% number,
  once rephrased as "can we eliminate rug-pull by file hashing," once as
  "are the 13-27% structurally compatible... as an effective strategy").
  Each time: coverage = can the defense even be pointed at this
  deployment (architectural question); effectiveness/elimination = does
  it actually stop attacks (requires knowing real-world attack incidence,
  which is unmeasurable because silent rug-pulls are invisible to current
  tooling by definition). **If this comes up a fourth time, the fix is:
  ask "structurally reachable by X" vs. "stops attacks," never let
  "effective" or "eliminate" describe a reachability number.**
- **"Is this even a real issue" is answered by the mechanism experiment
  (existence proof), never by a percentage.** A coverage/prevalence number
  cannot answer "is this real" — only "how far could a known-real thing's
  fix reach."
- **"Rug pull" is an overloaded industry term** — this project means
  interface-preserving implementation change, specifically not Microsoft's
  agent-to-agent framing or Pillar's CI/CD privilege-escalation framing.
  State this explicitly in the paper (`preprint.md` §1.1) — don't assume
  the term disambiguates itself.
- **User's core standard for this pivot, stated directly, keep applying
  it**: "concrete and sharp, not a hypothesis supported by toy servers... I
  am a single person, they probably took months." Any proposed direction
  that requires large-scale scraping, new infrastructure, or matching a
  multi-person team's data-collection scale should be rejected on sight
  without needing a full novelty search first — the solo/4-day constraint
  rules it out regardless of novelty.

## File status (read this before opening the other files)

- **`preprint.md`** (repo root) — **current, active draft.** Start here.
- **`claude/progress-report.md`** (this file) — current, rewritten this
  session, source of truth for project state.
- **`research-plan.md`** (repo root) — **STALE.** Written for the
  pre-pivot plan (coverage measurement + 3-4 real-server extension as the
  headline). Not deleted because Part 1's method description and the
  original novelty-check literature list are still accurate and useful,
  but its framing of "what the contribution is" no longer matches
  `preprint.md`. Needs a rewrite pass or an explicit superseded-by note at
  the top if it's kept around — don't draft from it without cross-checking
  against this file first.
- **`claude/preprint-frame.md`** — **mostly stale.** Written mid-session on
  2026-09-17 before the pivot; its sections 3-7 describe the abandoned
  coverage-measurement framing. Section 2 ("what exists today") is still
  useful raw material (verified tool/paper facts), but read it as source
  material, not as the current plan.

## Loose ends

- *(Carried over, still open)*: revoke the GitHub PAT
  (`ghp_CPbCW8...`) used for earlier code-search research, if not already
  done.
- Get exact repo URLs for hardened-mcp-server and mcpseal into
  `preprint.md`'s reference list (currently a TODO there).
- Find a citable source for the Clinejection npm-package incident
  (currently referenced from memory in `preprint.md` §2, marked TODO).
- If time allows after Gap 2 is done: consider whether the abandoned
  real-reference-server extension (time/fetch/filesystem) is worth adding
  as a stretch "extended validation" section — not required, don't start
  it before Gap 2 and the writeup are done.
