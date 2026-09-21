# Progress report — MCP tool integrity gap research

Status as of 2026-09-21, end of the fourth working session. **All four
planned experiments are now built, real, and independently verified —
this is the current state, superseding everything below about Gap 2
being "not yet run."** Read this whole file before touching
`research-plan.md` or `preprint-frame.md` — both are stale (see "File
status" at the bottom) and this file is the current source of truth.

## Git history note — read before assuming any file's history is complete

Partway through this session, a `git pull`/reset discovered that this
session's own earlier combined-architecture rewrite (a local commit,
"more brainsortimng," containing a fully restructured `preprint.md`,
`progress-report.md`, `preprint-frame.md`, plus `steps.md` and
`short-version.md`) had diverged from `origin/main` and was never
pushed. A separate machine had, in parallel, pushed real experiment
scaffolding (`scripts/experiment_1/`, `scripts/experiment_2/`) built on
an *earlier* point in the history. Pulling reset this checkout to
`origin/main`, which kept the real code but dropped this session's
writing commit — it's not deleted, just orphaned (recoverable via
`git show 7201b49` as long as reflog hasn't expired it). Per explicit
instruction, that divergence was **not reconciled** — all work since has
built forward from `origin/main`'s state, not merged with the dangling
commit. `steps.md` and `short-version.md` are consequently gone from
disk and were not recreated. If you want that dangling content back,
check reflog before it expires; don't assume it's silently gone forever.

## The research question (current, final wording)

Every current MCP "rug-pull" defense hashes or signs some subset of a
tool's *declared interface* (name, description, schema), never its
implementation. That specific gap is already known/self-acknowledged by
several tools — proving it exists again is not the contribution. What
hasn't been done: (1) a **precise, field-by-field audit** of exactly what
every real, currently-deployed defense actually covers and exactly where
each one stops, and (2) showing that **even the best of them has its own
further boundary**, demonstrated in three nested layers on a real
reference server, not asserted: interface vs. implementation (Gap 1),
local closure vs. package-manager dependency (Gap 2), and any static
hash at all vs. a dormant, threshold-gated trigger (Gap 3) — plus a
combined run showing a static+canary architecture together catches all
three, which neither layer catches alone.

Three nested claims, all done:
- **Gap 1** (interface vs. implementation): proven, real server, reproducible.
- **Gap 2** (local closure vs. package-manager dependency): proven, real
  server, real dependency, calls the real `tooldex` package directly —
  **and corrected a wrong assumption this project started with about
  Tooldex along the way** (see below).
- **Gap 3** (any static hash vs. a dormant trigger): proven, real server,
  reproducible.
- **Combined run**: all three scenarios together against a unified
  static+canary decision rule — built, reproducible.

## What's done and verified

### 1. The preprint draft: `preprint.md` (repo root)

Fully rewritten this session to match. Structure: intro + terminology
scoping (§1.1) → threat model (§2) → the field-level audit table (§3,
corrected — see below) → Experiment 1/Gap 1 (§4, real numbers) →
Experiment 2/Gap 2 (§5, real numbers, corrected finding) → Experiment
3/Gap 3 (§6, real numbers) → discussion/limitations/conclusion
(renumbered §7-9, updated for three gaps not two).

**Nothing is left as a TODO placeholder for results** — all three
experiments and the combined run have real, reproducible numbers pasted
into the document. Remaining TODOs are genuinely just writing/judgment
calls (the abstract, the conclusion's final prose), not research tasks.

### 2. A correction discovered mid-build, not assumed away

The original plan for Gap 2 assumed Tooldex's `trust_store.py` hashes
only the entry-point file. **Checked directly** (`inspect.getsource` on
the real, published v1.0.2 package): it already walks *down* from the
entry point's own directory, hashing every recognized local source file
in that tree — much closer to a "whole-closure hash" than this project
originally gave it credit for. What it deliberately excludes, per its
own docstring, is package-manager-installed dependency directories
(`node_modules`, `venv`, `.venv`, `env`). This reframed Gap 2 from "any
imported file" (not real, as it turns out) to "specifically a
package-manager-delivered compromise" (real, demonstrated in Experiment
2) — a sharper, more realistic finding than the original plan, found by
checking rather than assuming.

### 3. All four experiments — real server, real code, built and verified twice (this machine and the user's)

All four live in `scripts/experiment_{1,2,3,4}/`, sharing one vendored,
unmodified copy of Anthropic's real `filesystem` MCP reference server in
`scripts/vendor/filesystem-server/` (not committed — gitignored
`node_modules`/`dist`). Each has a `README.md` with exact run
instructions and a `Dockerfile`; every one of the four was built AND run
in Docker, not just written, before being reported as working — and the
user independently reproduced Experiments 1 and 2 on their own machine
with byte-for-byte identical hashes.

- **Experiment 1 (Gap 1)**: mutates `readTextFileHandler` (defined
  inline in the server's own `index.ts`) to leak the OS username. Wire
  hash unchanged, file hash changed, real output changed.
- **Experiment 2 (Gap 2)**: mutates `minimatch`, a real npm dependency
  the server actually uses (via `lib.ts`'s `searchFilesWithValidation`).
  Calls Tooldex's real `trust_store.set_decision()` /
  `files_changed_since_approval()` directly — not a reimplementation.
  Wire hash, Tooldex's real check, and a local-closure hash all miss it;
  a new lockfile-depth hash (hash-of-hashes over the resolved
  `node_modules/minimatch/` directory) catches it. Hit and fixed a real
  bug: minimatch's ESM `exports` map resolves `import` to
  `dist/esm/index.js`, not `dist/commonjs/index.js` (the `main`
  field/`require` condition) — mutating the wrong file silently changed
  nothing, caught by testing each file in isolation before trusting
  either result.
- **Experiment 3 (Gap 3)**: writes a module-level call counter and a
  threshold-gated branch into `index.ts` *once* — normal for calls 1-3,
  a leak on call 4 — never mutated again mid-run. One live session, four
  calls. Wire hash and local-closure hash identical before/after the
  whole session (nothing on disk ever changes); a canary baseline from
  call 1 catches call 4's deviation. Structurally different from
  Experiments 1/2: not "the hash looked in the wrong place," but "there
  was nothing for any hash to ever see change."
- **Experiment 4 (combined run)**: not a new gap — orchestrates the same
  three mutations against one unified static layer (local-closure +
  lockfile-depth, as one hash) and one canary layer, under a combined
  decision rule. Result: rows 1 and 2 caught by the static layer alone;
  row 3 (the dormant trigger) caught *only* because of the canary
  layer — the entire argument for the combined architecture in one
  table.

### 4. The field-level audit table (`preprint.md` §3) — corrected

| Defense | Covers | Stops at |
|---|---|---|
| ETDI (arXiv 2506.01333) | name, description, schema, permissions, optional hash of backend *API contract* (OpenAPI/Swagger) | the API contract, not backend code |
| mcpseal | name, description, schema | self-acknowledged limitation |
| hardened-mcp-server | raw wire object, best of 20 policies | self-acknowledged limitation |
| mcp-pin / Plumbline | name, description, schema, annotations (RFC 8785) | confirmed via its own 2026-09-03 finding doc — still metadata-only |
| Vercel AI SDK `detectToolDrift` (`ai@7.0.19`, shipped July 2026) | description, resolved schema, title | metadata-only, shipped mainstream SDK feature with the same blind spot |
| MCP Manager (mcpmanager.ai) Feature Governance | name, title, description | confirmed directly from their docs — no schema, no implementation |
| Microsoft APM (`microsoft.github.io/apm`, `github.com/microsoft/apm`) | full content hash of declared agent-context packages, via lockfile | **install-time only**; different artifact class |
| **Tooldex `trust_store.py`** | full content of every recognized local file, walking *down* from the entry point's own directory — **corrected this session, was previously and incorrectly characterized as entry-point-only** | explicitly excludes `node_modules`/`venv`/etc. by design (this is Gap 2) |
| This work (Gap 3) | the above **+** a canary output check across repeated calls | nothing left within this project's own demonstrated scope; generalizing canary-input selection to arbitrary tools remains open |

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

All research/implementation work is done. What's left is writing and
judgment calls, not new experiments:

1. Write the abstract (§Abstract) and conclusion (§9) — deliberately left
   for last, per standard practice, both scaffolded with guidance already.
2. Decide whether to keep or cut `preprint.md` §7.3 (the paragraph
   explaining why the population-measurement direction was dropped) —
   recommended to keep, short, as already drafted.
3. Fill remaining citation TODOs in `preprint.md` References (exact repo
   URLs for hardened-mcp-server and mcpseal; Clinejection incident
   source).
4. Optional, not required: decide whether to pursue any of the explicitly
   out-of-scope extensions named in §6 (the `npx`/`uvx` canary extension,
   the organic-traffic canary variant, non-deterministic-tool support) —
   none of these are needed to consider the current draft complete.

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
