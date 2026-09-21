# Where MCP Tool Integrity Checks Stop: A Field-Level Comparison and a Minimal Lockfile-Depth Fix

**Author:** Ria Banerjee
**Status:** Draft — sections marked `TODO` need your input/results before submission.
**Competing interests:** The author is the sole developer of Tooldex, one
of the eight systems evaluated in this paper (§3, §5). No other competing
interests are declared.

---

## Abstract

> **TODO (you):** write last, 150–200 words. Should state: (1) every
> current MCP "rug-pull" defense hashes or signs some subset of a tool's
> *declared interface*, never its implementation — demonstrated on a
> real reference server (Anthropic's official `filesystem` MCP server),
> not a hand-built example; (2) the obvious fix — hashing the server's
> local files — turns out to already be what Tooldex's real,
> published `trust_store.py` does (a correction from this project's own
> earlier, incorrect assumption, confirmed by reading its actual
> source), and it is necessary but not sufficient: it stops precisely at
> package-manager-installed dependencies, by design; (3) a second
> experiment, against a real npm dependency the target server actually
> uses, and calling Tooldex's real code directly (not a reimplementation),
> shows this boundary is real and shows a minimal lockfile-depth
> extension — specified but left unbuilt earlier in this project — that
> closes it; (4) a third experiment shows that even that extension has a
> structural limit — a dormant, threshold-gated trigger present from
> first deployment, invisible to any static hash because the file never
> changes — closed only by comparing repeated real outputs against a
> canary baseline.

---

## 1. Introduction

The Model Context Protocol (MCP) lets an AI agent call external tools
through a declared interface: a name, a natural-language description, and
a JSON input schema. A client approves a tool once, based on that
interface, and then trusts it indefinitely. A **"rug pull"** is when the
tool's actual behavior changes after that approval without the interface
changing — the client has no signal that anything is different, because it
never re-inspects anything beyond what it originally approved.

This is not a hypothetical concern. It is named explicitly in:

- OWASP's MCP Top 10, [MCP04:2025 – Software Supply Chain Attacks &
  Dependency Tampering](https://owasp.org/www-project-mcp-top-10/2025/MCP04-2025%E2%80%93Software-Supply-Chain-Attacks&Dependency-Tampering)
- Microsoft's Zero Trust attack-technique catalog, ["Rug-Pull Attack (Agent
  / MCP Server)"](https://learn.microsoft.com/en-us/security/zero-trust/catalog-ai-attack-techniques/rug-pull-attack)
  (dated July 2026)
- The paper that coined the term for MCP, ETDI (arXiv 2506.01333)

and it is the acknowledged, self-reported limitation of at least three
independent, actively-maintained defense projects (§3).

**What's missing is precision, not awareness.** Every source above states
that "interface-preserving behavior changes are a problem" in general
terms. None of them states *exactly* where each real defense's coverage
actually stops. This paper does both, and corrects an assumption it
started with along the way:

1. A field-by-field audit of real, currently-deployed or
   currently-proposed MCP integrity mechanisms, showing precisely which
   fields each one covers and where each one stops (§3) — including
   reading Tooldex's own real, published source directly rather than
   assuming its scope, which overturned this project's own earlier
   characterization of it as entry-point-only.
2. A reproducible demonstration, on a real reference server rather than
   a hand-built example, that wire-level interface hashing misses a
   schema-preserving behavior change (§4, Gap 1).
3. A second reproducible demonstration, against a real npm dependency
   and Tooldex's real code (not a reimplementation), that even Tooldex's
   actual local-closure hash — already more complete than this project
   first assumed — stops precisely at package-manager-installed
   dependencies, and that a minimal lockfile-depth extension, run here
   for the first time rather than only specified, closes that boundary
   (§5, Gap 2).
4. A third reproducible demonstration that no static hash — however
   complete, including the lockfile-depth extension from Gap 2 — can
   ever detect a malicious trigger present from first deployment that
   never touches disk again, and that only comparing a tool's own real
   output across repeated calls against a canary baseline catches it
   (§6, Gap 3).

### 1.1 Terminology scope (read this before citing "rug pull" elsewhere)

"Rug pull" is used inconsistently across sources currently in this space.
This paper uses it in exactly one sense — **interface-preserving change to
a single tool's implementation** — and explicitly *not* in the sense used
by:

- Microsoft's Zero Trust catalog page, which describes agent-to-agent
  prompt injection via a compromised or impersonating *peer agent* in a
  multi-agent directory — a trust/authorization failure, not an
  interface/implementation mismatch.
- Pillar Security's report on Google's `adk-python` repository, which
  describes a CI/CD privilege-escalation / confused-deputy bug (a
  low-privilege bot triggering a high-privilege workflow) — unrelated to
  tool interface integrity.

> **TODO (you):** confirm you want to keep this scoping paragraph near the
> top — it pre-empts a reviewer conflating your claim with either of those.

---

## 2. Threat model

A tool's implementation can change without its interface changing through
several ordinary, already-observed channels — not only "an attacker
breaks into your laptop":

- **Compromised transitive dependency.** The entry-point file is
  untouched; a package it imports gets a malicious version pushed to
  PyPI/npm. Real precedent: **Clinejection**, a malicious npm package
  version live for ~8 hours, February 2026. §5 demonstrates the exact
  mechanism this describes, not just its plausibility: a real npm
  dependency (`minimatch`) of a real reference server, mutated in place,
  invisible to wire hashing and to Tooldex's real, current
  `trust_store.py` alike.
  > **TODO (you):** add the exact source/link for the Clinejection incident
  > if you want it citable rather than referenced from memory.
- **Compromised upstream repository.** A locally-run server is a cloned
  git repo (`git clone ... && python server.py`); a compromised maintainer
  account or a merged malicious PR lands in the next `git pull`, and the
  new (also legitimately re-signed, if the repo does that) content becomes
  the new baseline without triggering scrutiny.
- **General local compromise.** Any other process with filesystem write
  access (malware, a compromised IDE extension) can edit the server file
  directly; the MCP server is simply one of many things such a foothold
  could tamper with, and an attractive one because it inherits whatever
  permissions the tool already has.
- **Malicious or compromised insider**, where the "server" is an
  internally shared script multiple engineers pull from.

None of these require defeating anything at the protocol layer — they all
land as an ordinary file-content change, which is exactly the layer none
of the defenses in §3 inspect.

**This is not a rare pattern at real ecosystem scale.** A Snyk-owned
project (`snyk/agent-scan`, issue #482) measured, across 7,949
multi-version MCP servers and 59,821 real release transitions in the
public registry, that **74.6%** of releases kept the tool's presented
interface identical while the resolved package version changed
underneath. That figure isn't a measurement of malicious activity — most
of those releases are ordinary, benign updates — but it confirms that
"interface stays constant while the implementation changes" is the
*overwhelmingly common* shape of a real MCP release, not a contrived
edge case invented for this paper. Any defense that stops at the
interface is structurally blind to the large majority of real update
activity, benign or malicious, by this measurement.

That same issue proposes a different dynamic signal than this paper
builds: watching for *capability expansion* at runtime (newly-accessed
network hosts, secrets, or filesystem writes) rather than comparing a
tool's own output against a canary baseline. A real, credible,
differently-shaped answer to the same motivating problem — closer to
the OS/process-level runtime monitoring family (§3) than to this
paper's deterministic canary check — not evaluated here, but worth
knowing it exists as an alternative, not a competing claim on the same
mechanism.

---

## 3. Field-level audit of current MCP integrity mechanisms

Every source below was read directly (not paraphrased from a secondary
summary) to confirm the exact scope of what it checks.

| Defense | Exact fields covered | Re-verification timing | Reaches dependency closure? |
|---|---|---|---|
| **ETDI** (arXiv 2506.01333) | name, description, input schema, permissions; optionally a hash of the tool's backend *API contract* (e.g. an OpenAPI/Swagger spec) | On reconnect; signature re-verified against stored public key | **No** — an OpenAPI contract describes the interface a backend promises, not what its code does; also conditional on the tool having a documented REST contract at all |
| **mcpseal** | name, description, input schema | On connect | No — states this as its own limitation |
| **hardened-mcp-server** | raw wire object {name, description, schema}, best-performing of 20 policies tested | On connect | No — states launch-command binding is "weaker than hashing executable contents" |
| **mcp-pin / Plumbline** | name, description, input schema, annotations, RFC 8785-canonicalized | Periodic crawl; append-only transparency log | No — confirmed via its own 2026-09-03 finding doc |
| **Vercel AI SDK** (`fingerprintTools`/`detectToolDrift`, `ai@7.0.19`, July 2026) | description, resolved input schema, title | On demand, baseline storage is the app's responsibility | No |
| **MCP Manager** (Feature Governance) | name, title, description (developer-selectable granularity) | Per allowlist check | No — explicitly no schema or implementation matching |
| **Microsoft APM** | full content hash of declared agent-context packages (skills, prompts, MCP servers), via lockfile | **Install-time only**; `apm audit` is manual/opt-in and diffs local hand-edits, not upstream changes | Partial — hashes real content, but for a different artifact class (agent-context packages, not a live MCP server at the moment of tool invocation) and without automatic per-call re-verification |
| **Tooldex `trust_store.py`** | full content of every recognized local source file reachable by walking *down* from the entry point's own directory — confirmed by reading the real, published v1.0.2 source directly (`inspect.getsource`), not assumed | On connect | **Partial** — correctly covers the local closure (this is *not* entry-point-only, correcting an earlier, incorrect characterization in this project); explicitly excludes package-manager dependency directories (`node_modules`, `venv`, `.venv`, `env`) by design — "pinning an entire node_modules tree is a different, impractical problem," per its own docstring |
| **This work (demonstrated, §5)** | Tooldex's real local-closure hash **+** a hash-of-hashes over the resolved `node_modules` (or equivalent) dependency directory | On connect | **Yes**, for local files and installed package-manager dependencies both |

**Reading the table:** every row stops at a different boundary. Tooldex's
own hash — the strongest of the existing, deployed options, and already
closer to a full local-closure hash than this project originally gave it
credit for — is necessary but not sufficient: it stops precisely at the
boundary of package-manager-installed dependencies, deliberately, by its
own design. That specific, previously unquantified boundary — not "does
Tooldex hash more than one file" (it already does) but "does anything
reach inside an installed dependency" (nothing does) — is the gap this
paper closes.

> **TODO (you):** if you find a defense not in this table, verify its exact
> scope by reading primary docs/source directly (not a blog summary)
> before adding a row — that standard was applied to every row above.

---

## 4. Experiment 1 — the interface/implementation gap is real (Gap 1)

**Setup, on a real reference server, not a toy one.** The target is
Anthropic's own official `filesystem` MCP server
(`modelcontextprotocol/servers`, `src/filesystem`), vendored unmodified
into `scripts/vendor/filesystem-server/`. Not an obscure example: the
published package gets 232,701 weekly downloads with 41 other packages
depending on it directly, and was last updated 19 days before this was
written — every experiment in this paper runs against code actually
executing in a large number of real, active deployments, not a
hypothetical one. `scripts/experiment_1/run_experiment.py`
mutates `readTextFileHandler` — defined *inline* in the server's own
`index.ts`, used by both the `read_file` and `read_text_file` tools — to
append the OS username to every file read, without touching the tool's
registered name, description, or input schema a few lines below in the
same file. Interface byte-for-byte identical; behavior different. All
three signals compared via real MCP protocol calls (`tools/list`,
`tools/call`) against the server's actual TypeScript source, run
directly via `npx tsx` (no separate build step to go stale between
mutations) — not static inspection.

- **Wire hash** — sha256 of canonicalized `{name, description,
  inputSchema}` for `read_text_file` — replicates hardened-mcp-server's
  best-performing policy.
- **File hash** — sha256 of `index.ts`'s bytes — what a naive
  entry-point-only hash would pin.
- **Real output** — an actual `tools/call("read_text_file", {"path": "hello.txt"})`
  against a real fixture file.

**Result** (reproducible — rerun with
`uv run --no-project --with mcp python3 scripts/experiment_1/run_experiment.py`,
or via `scripts/experiment_1/Dockerfile`; see its README for exact commands):

```
v1 wire hash: 1d8b2b6ca5e1073726f4f41ba61ac8c888d2867157d6cf12547c55051c7f482a
v2 wire hash: 1d8b2b6ca5e1073726f4f41ba61ac8c888d2867157d6cf12547c55051c7f482a  <- UNCHANGED
v1 file hash: bff21de612c59d64b351f70615f44563f0efe76666a75aa52450ebe6fae6584a
v2 file hash: df22fe18a5b18f77443ffde9e8da4b02450ad20be7c9abe3a9fcf21cb420469e  <- CHANGED
v1 output: 'hello world\n'
v2 output: 'hello world\n\n[leaked-user:ria]'  <- CHANGED (real leak, not simulated)
```

**Reading:** wire-level hashing — what six of the seven existing defenses
in §3.1 rely on — does not detect the change, on Anthropic's own real,
popular reference implementation, not a hand-built example. File hashing
does. This confirms, mechanically rather than by assertion and on real
production code, the limitation that mcpseal, mcp-pin, and
hardened-mcp-server each already state about themselves in their own
documentation.

> **TODO (you):** data is final and reproducible. This replaces the
> earlier toy-echo-server version of this experiment — see
> `scripts/experiment_1/README.md` for the exact mutation and the
> ESM-vs-CommonJS gotcha that came up building Experiment 2 (§5), worth
> knowing about if you extend this to a different tool.

---

## 5. Experiment 2 — even Tooldex's real local-closure hash has a boundary (Gap 2)

**Motivation, corrected from the original plan.** The original framing
assumed Tooldex's `trust_store.py` hashes only the entry-point file. That
assumption was wrong, and checking it directly is what this section
actually demonstrates. Read from the real, published source
(`inspect.getsource(trust_store)`, v1.0.2): it already walks *down* from
the entry point's own directory, hashing every recognized local source
file in that tree. What it deliberately excludes, per its own docstring,
is package-manager-installed dependency directories — `node_modules`,
`venv`, `.venv`, `env` — "pinning an entire node_modules tree is a
different, impractical problem." So the real boundary isn't "any
imported file"; it's specifically a compromise delivered through a
package-manager dependency. That's what this experiment demonstrates,
using a dependency the target server already actually uses — not a
hand-placed stand-in.

**Setup, on the same real server as Experiment 1, calling Tooldex's real
code, not a reimplementation.** `scripts/experiment_2/run_experiment.py`
mutates `minimatch` — a real npm package the `filesystem` server imports
and calls from `lib.ts`'s `searchFilesWithValidation`, used by the
`search_files` tool for both its main pattern match and its
`excludePatterns` check — so that `minimatch()` always returns `true`.
Real consequence: `search_files` with pattern `*.txt` starts returning
every file in the searched directory, not just `.txt` files, including
one that was never supposed to match at all. The experiment calls
Tooldex's actual `trust_store.set_decision()` and
`files_changed_since_approval()` functions directly, from the real
`tooldex==1.0.2` PyPI release.

One implementation detail that mattered and is worth recording: the
server's `package.json` has `"type": "module"`, so `import { minimatch }`
resolves via minimatch's own `exports` map's `"import"` condition
(`dist/esm/index.js`), not the `"require"` condition
(`dist/commonjs/index.js`, also minimatch's legacy `main` field).
Mutating the CommonJS file first produced a build that ran fine but
changed nothing observable — confirmed by testing each file in isolation
before trusting either result, not assumed.

**Four signals, not three:**

- **Wire hash** — expected unchanged (schema untouched).
- **Tooldex's real `files_changed_since_approval()`** — expected to say
  unchanged (node_modules pruned by design — this is the point).
- **Local-closure hash** — this project's original Gap-2-era proposal
  (entry point + local siblings, still no `node_modules`) — expected
  *also* unchanged, for the same reason: it's a narrower restatement of
  what Tooldex already does, not an extension past it.
- **Lockfile-depth hash** — a hash-of-hashes over the resolved
  `node_modules/minimatch/` directory, established as a baseline and
  re-checked later, the same mechanism as the closure hash applied one
  level deeper — expected **changed**. This is the §4.1-equivalent
  extension this project had previously left as specified-but-not-built;
  this is the first time it's actually run.
- **Real output** — expected changed.

**Result** (reproducible — rerun with
`uv run --no-project --with tooldex==1.0.2 --with mcp python3 scripts/experiment_2/run_experiment.py`,
or via `scripts/experiment_2/Dockerfile`; see its README for exact commands):

```
v1 wire hash:            41f144836f5e786009e2173256759e37b687add572cfba808e24bebb9a04ce96
v2 wire hash:             41f144836f5e786009e2173256759e37b687add572cfba808e24bebb9a04ce96  <- UNCHANGED
v1 local-closure hash:    cbfe87a6e127f67f017f5a544586948a01904f1ea8aaaf7477b2ca94f0ea9c31
v2 local-closure hash:    cbfe87a6e127f67f017f5a544586948a01904f1ea8aaaf7477b2ca94f0ea9c31  <- UNCHANGED
v1 lockfile-depth hash:   1f9396b09daf5a67335c2ecc6fac29cce9797b22f2827f3de219bb5c7b67a143
v2 lockfile-depth hash:   f21580de5e6a6ae921a21fff647857d8a7ee1bb3e6d2d621d7f61345ec91db63  <- CHANGED
v1 output: '.../a.txt', '.../b.txt'
v2 output: '.../a.txt', '.../b.txt', '.../secret.env'  <- CHANGED (real leak, not simulated)
Tooldex's real files_changed_since_approval(): False
```

**Reading:** a real npm dependency compromise is invisible to wire
hashing, invisible to Tooldex's real, current `trust_store.py`, and
invisible to this project's own originally-proposed local-closure
hash — all three stop at the same boundary, `node_modules`, deliberately
excluded by design in Tooldex's case. Only extending the hash to the
resolved dependency's own directory — the lockfile-depth extension —
catches it. This is a sharper, more realistic version of "Gap 2" than
originally planned: not an artificial sibling-file split, but the actual
delivery mechanism most real supply-chain compromises use.

**Reference implementation note:** the lockfile-depth hash does not
require new cryptography — it's the same "hash of hashes" pattern
(`sha256(sorted(sha256(f) for f in resolved_package_dir.rglob("*")))`)
already standard practice in npm's `package-lock.json` `integrity` field
and pip's `--require-hashes` lockfiles (§7.2), just applied to the
resolved on-disk package directory as a drift baseline rather than
re-verified against the original published tarball each time — a
narrower, honestly-scoped property (catches drift since *your* approval,
not compromise before it) matching what the local-closure hash already
does one level up.

---

## 6. Experiment 3 — a dormant trigger defeats every static hash (Gap 3)

**Motivation.** Experiments 1 and 2 both show a hash *missing* a change
because it isn't looking in the right place — the file itself, or a
dependency. This experiment asks a structurally different question: can
any static hash — wire-level, local-closure, or even the lockfile-depth
extension that closed Experiment 2's gap — detect a malicious trigger
that was present in the code from the moment it was deployed and never
touches disk again afterward? It cannot, not because the hash is
incomplete, but because there is nothing on disk for it to ever see
change.

This is not a hypothetical framing invented for this paper. The same
pattern — a server that behaves honestly for a number of calls before
defecting once some threshold is crossed — is independently named and
benchmarked as a real threat class ("TrustShift") in published research
on staged MCP server compromise (["TrustShiftProbe"](https://arxiv.org/pdf/2608.23763),
arXiv 2608.23763), and is separately reported as a real incident by
[`mcp-behaviour-guard`](https://github.com/hacker-vs-cracker/mcp-behaviour-guard)'s
own findings ("Deadbugz"): a server behaving normally for three calls
before changing behavior on the fourth.

**Setup, on the same real server as Experiments 1 and 2.**
`scripts/experiment_3/run_experiment.py` writes `index.ts` *once* — a
module-level call counter and a threshold-gated branch inside
`readTextFileHandler`: normal behavior for the first 3 calls, a leak
appended starting on the 4th. Unlike Experiments 1 and 2, this file is
never rewritten mid-run — the counter's state lives in the running
process's memory, not on disk, which is exactly what makes it invisible
to a hash taken at any point in that lifetime. One server process, one
live session, four calls made within it — not a fresh process per
call — because the trigger's state has to persist across calls the way
it would for a real long-running MCP session.

**Four signals:**

- **Wire hash** — taken once, mid-session — expected unchanged.
- **Local-closure hash** — taken once before the session and once
  after — expected **identical both times**. The load-bearing result:
  not "unchanged between two versions" as in Experiments 1/2, but
  "unchanged because there was never a second version."
- **Canary output hash** — the first call's output, hashed and treated
  as a baseline; every later call's output compared against it —
  expected to match for calls 1–3, mismatch on call 4.
- **Real output** — expected identical for calls 1–3, different on
  call 4.

**Result** (reproducible — rerun with
`uv run --no-project --with mcp python3 scripts/experiment_3/run_experiment.py`,
or via `scripts/experiment_3/Dockerfile`):

```
local-closure hash before the session: 85d698f77adc594353b2f7fdcdadbc6ecda4013e68f4d9fd577dbc29f18efe02
local-closure hash after 4 calls:      85d698f77adc594353b2f7fdcdadbc6ecda4013e68f4d9fd577dbc29f18efe02  <- IDENTICAL
wire hash (taken once, mid-session):   1d8b2b6ca5e1073726f4f41ba61ac8c888d2867157d6cf12547c55051c7f482a

call 1: 'hello world\n'                          [matches canary baseline]
call 2: 'hello world\n'                          [matches canary baseline]
call 3: 'hello world\n'                          [matches canary baseline]
call 4: 'hello world\n\n[leaked-user:ria]'        [MISMATCH — flagged]
```

**Reading:** across the entire session, the file on disk never changes,
so both the wire hash and the local-closure hash are identical whether
taken before the first call or after the last. Every static check in
this paper's own toolkit — including the fix that closed Gap 2 — reports
"unchanged" the whole time. Only comparing each call's real output
against a canary baseline established from an earlier call catches the
change, and only on the exact call where it actually happens.

**Combined run.** `scripts/experiment_4/run_experiment.py` runs all
three scenarios above back to back against one unified static layer
(local-closure hash + the resolved dependency directory, as one
hash-of-hashes) and one canary layer, under the combined decision rule
from §4.3 — flag if either layer moves. Not a new experiment; the same
mutations and signals already built for Experiments 1–3, orchestrated
together. Reproducible result:

```
Scenario                         Static     Canary     Combined
1 — interface-preserving edit    CHANGED    CHANGED    CAUGHT
2 — dependency compromise        CHANGED    CHANGED    CAUGHT
3 — dormant trigger              unchanged  CHANGED    CAUGHT
```

Row 3 is the entire argument for the combined architecture in one line:
it is the only row where the static layer — even including the
lockfile-depth extension that closed Gap 2 — reports nothing wrong,
because nothing on disk ever changed. The canary layer catches it
regardless, and the combined rule catches every row.

---

## 7. Discussion

### 7.1 What this does and does not claim

- **Does claim:** a specific, previously-unstated structural boundary
  exists in every current MCP integrity mechanism, at two nested levels
  (interface vs. implementation; entry-point vs. dependency closure), and
  that boundary is closable with a straightforward extension of the
  already-most-rigorous deployed option (file hashing).
- **Does not claim:** any measurement of how often this is exploited in
  the wild — silent, interface-preserving changes are by construction
  invisible to every current detection method, so no incidence rate is
  derivable from existing data.
- **Does not claim:** this fixes the majority of real MCP deployments.
  Servers launched via `npx`/`uvx` fetch code fresh from a registry with
  no stable local file at all; whole-closure hashing, like plain file
  hashing, cannot apply to them — this is specific to *hashing*, not a
  limit on integrity verification in general (§7.3 names the distinction).
- **Does not claim** that closing this gap "eliminates" rug-pull risk even
  where it applies. Hashing is a *detection* mechanism; ETDI's own paper
  notes "users are unlikely to scrutinize a tool they believe they have
  already vetted" — a correctly-triggered re-approval prompt can still be
  clicked through. This paper's contribution stops at detection coverage,
  not human response to detection.

### 7.2 Why "hash of hashes," not a full Merkle tree

A full Merkle tree earns its cost when you need partial proofs (verify one
dependency without the full set) or operate at a scale where O(log n)
matters. A single MCP server's dependency count doesn't warrant that
machinery — a flat hash over the sorted set of per-file hashes gives the
same tamper-evidence property. Noting this explicitly to avoid
over-engineering a solution to a small-scale problem.

### 7.3 The population question — deliberately out of scope here

An earlier direction for this project attempted to measure what fraction
of real-world MCP deployments are even local-file-launched (as opposed to
`npx`/`uvx`) across two convenience samples. That measurement is *not*
included here because:

- The methodological bar in this exact space is already set high by
  **["Same Name, Different Server: A Security Census of Silent Drift in
  the MCP Ecosystem"](https://arxiv.org/html/2609.14119)** (arXiv
  2609.14119) — a full registry census (21,643 servers, source fetched for
  14,353, an 8-class scanner validated against 414 hand-labeled findings).
  Notably, that paper's own stated limitation is that "the registry does
  not version tool definitions, so a behavioural change is invisible in
  registry data by construction" — i.e. even that census cannot see what
  this paper demonstrates directly. This paper is a small, hand-verified
  complement to that census's explicitly named blind spot, not a
  competing population estimate.
- General dependency pinning-vs-floating prevalence is already measured
  at ecosystem scale by ["A Large Scale Analysis of Semantic Versioning in
  NPM"](https://arxiv.org/abs/2304.00394) (arXiv 2304.00394) and ["Which
  Is Better For Reducing Outdated and Vulnerable Dependencies: Pinning or
  Floating?"](https://arxiv.org/abs/2510.08609) (arXiv 2510.08609,
  survival analysis across npm/PyPI/Cargo).
- ["Pinning Is Futile"](https://arxiv.org/pdf/2502.06662) (arXiv
  2502.06662, CMU, FSE) is a direct, credible caution against treating
  pinning/hashing as sufficient supply-chain defense on its own —
  engaged with here rather than ignored: this paper's contribution is
  narrowly about *detection coverage at the MCP client trust-gate
  moment*, not a general supply-chain security claim, and does not
  contest that caution.

> **TODO (you):** decide whether to keep this subsection or cut it
> entirely. Arguments for keeping: pre-empts an obvious reviewer question
> ("didn't you measure this before?"/"why not a bigger study?"). Arguments
> for cutting: it spends words on what the paper *isn't* rather than what
> it is. Recommend keeping it short, as drafted, not expanding it.

**Why this is a hashing-specific limit, not a general one — named here,
not built here.** Everything above is about hashing specifically, which
structurally requires a stable local file. A different technique —
calling the tool over the protocol with a fixed input and checking its
response, rather than reading its bytes — has no such requirement: it
works identically whether the server was launched from a local script,
`npx some-package`, or `uvx some-tool`, because it never touches the
filesystem at all — §6's canary check is exactly this technique, though
demonstrated there for the dormant-trigger case, not yet for extending
reach to `npx`/`uvx`-launched servers specifically. This paper
deliberately keeps its demonstrated scope to local-file servers (§4,
§5) and does not build or test the `npx`/`uvx` extension. Two things
would need solving first, and
are named here rather than left as a vague gesture at future work: (1)
whether an existing behavioral/transport-boundary defense already covers
this implicitly, simply by not caring how the server started, which
would need checking before claiming it as new; and (2) a tolerance model
for legitimate version churn — an `npx`-launched server can resolve to a
newer, entirely legitimate release between sessions with nothing
malicious happening, so a behavioral baseline for such a server needs to
distinguish that from an actual rug pull, unlike a pinned local file,
which only changes when something — legitimate or not — actually edits
it.

---

## 8. Limitations

- **Small-N, hand-verified case study, not a population measurement.**
  Deliberate, per §7.3 — not a weakness to apologize for at length, just
  to state plainly.
- **Single implementer, single pass.** No independent replication yet.
- **All three experiments run against the same single real server**
  (Anthropic's official `filesystem` reference implementation) — not a
  toy example, but also not evidence across multiple, diverse real
  servers. Generalization beyond this one codebase is illustrative, not
  exhaustive.
- **No adoption or effectiveness claim.** This paper does not measure
  whether any client actually implements whole-closure hashing, nor
  whether users respond correctly to a triggered re-approval prompt.
- **Deliberately local-file scope only.** `npx`/`uvx`-launched servers
  are out of reach for hashing specifically, not for integrity
  verification in general — §7.3 names, but does not build, a
  non-hashing path that could reach them.
- **Gap 3's canary check is deterministic and single-tool.** It compares
  one fixed-input call's output against a baseline from an earlier
  identical call — it does not address a non-deterministic tool (an
  LLM-backed one, for instance) where repeated calls to unchanged code
  would legitimately produce different output, nor does it generalize
  the choice of canary input to arbitrary tools.

> **TODO (you):** add anything else you know is a real weakness —
> reviewers trust a limitations section more when it's specific rather
> than boilerplate.

---

## 9. Conclusion

> **TODO (you):** 3–5 sentences. Suggested shape: restate the three
> nested gaps (interface, dependency, dormancy), note that locating
> Gap 2 precisely required correcting this project's own initial
> assumption about Tooldex (not entry-point-only, as it turns out —
> confirmed by reading the real source, not assumed), restate that all
> three are demonstrated on the same real reference server, the second
> against a real npm dependency and Tooldex's real code (not toy
> examples or reimplementations), restate the lockfile-depth fix and
> that it's demonstrated (not just proposed) to close Gap 2, restate
> that Gap 3 shows a structural limit no static hash — however
> complete — can ever cross, closed only by the canary check, and close
> with the population-scale question (§7.3) as the explicit next-paper
> pointer rather than something this paper attempts.

---

## References

> **TODO (you):** convert to your target venue's citation format. URLs
> below were all directly verified (fetched/read primary source), not
> taken from secondary summaries.

1. ETDI: Mitigating Tool Squatting and Rug Pull Attacks in MCP —
   https://arxiv.org/pdf/2506.01333
2. OWASP MCP Top 10, MCP04:2025 – Software Supply Chain Attacks &
   Dependency Tampering —
   https://owasp.org/www-project-mcp-top-10/2025/MCP04-2025%E2%80%93Software-Supply-Chain-Attacks&Dependency-Tampering
3. Microsoft Learn, Rug-Pull Attack (Agent / MCP Server) —
   https://learn.microsoft.com/en-us/security/zero-trust/catalog-ai-attack-techniques/rug-pull-attack
4. Pillar Security, "I'll Just Call You Agent-to-Agent": Privilege Boundary
   Failures in CI/CD on Google's ADK Repository —
   https://www.pillar.security/blog/ill-just-call-you-agent-to-agent-privilege-boundary-failures-in-ci-cd-on-googles-adk-repository
5. mcp-pin, 2026-09-03 schema-drift finding —
   https://github.com/GautamTalksDev/mcp-pin/blob/main/docs/findings/2026-09-03-schema-drift.md
6. Plumbline — https://github.com/GautamTalksDev/Plumbline
7. Vercel AI SDK tool-drift detection (`ai@7.0.19`) —
   https://newreleases.io/project/github/vercel/ai/release/ai@7.0.19
8. MCP Manager, Feature Governance —
   https://docs.mcpmanager.ai/security/feature-governance
9. Microsoft Agent Package Manager (APM) — https://microsoft.github.io/apm/
   and https://github.com/microsoft/apm
10. "Same Name, Different Server: A Security Census of Silent Drift in the
    Model Context Protocol Ecosystem" — https://arxiv.org/html/2609.14119
11. "A Large Scale Analysis of Semantic Versioning in NPM" —
    https://arxiv.org/abs/2304.00394
12. "Which Is Better For Reducing Outdated and Vulnerable Dependencies:
    Pinning or Floating?" — https://arxiv.org/abs/2510.08609
13. "Pinning Is Futile: You Need More Than Local Dependency Versioning to
    Defend against Supply Chain Attacks" — https://arxiv.org/pdf/2502.06662
14. hardened-mcp-server (jkelly-dev1) — repository, direct doc quote in §3
15. mcpseal (confuseddude) — repository, direct doc quote in §3
16. `modelcontextprotocol/servers`, official MCP reference server
    implementations (target of Experiments 1–3) —
    https://github.com/modelcontextprotocol/servers
17. `minimatch`, real npm dependency mutated in Experiment 2 —
    https://www.npmjs.com/package/minimatch
18. Tooldex `trust_store.py`, real code called directly in Experiment 2 —
    https://pypi.org/project/tooldex/1.0.2/
19. "TrustShiftProbe: Characterizing, Benchmarking, and Defending Staged
    Trust Attacks on MCP Servers" — https://arxiv.org/pdf/2608.23763
20. `mcp-behaviour-guard`, incl. the "Deadbugz" delayed-activation
    finding, cited in §6 —
    https://github.com/hacker-vs-cracker/mcp-behaviour-guard
21. `snyk/agent-scan`, issue #482 — the 74.6% release-transition
    measurement and the capability-expansion proposal, cited in §2 —
    https://github.com/snyk/agent-scan/issues/482
22. `@modelcontextprotocol/server-filesystem`, npm package page (download
    / dependent-package statistics cited in §4) —
    https://www.npmjs.com/package/@modelcontextprotocol/server-filesystem

> **TODO (you):** add exact repo URLs for #14–15 if not already in
> `research-plan.md` — I have the quotes verified but should confirm the
> exact links are still on file before this goes out.
