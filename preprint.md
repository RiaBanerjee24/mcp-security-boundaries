# Where MCP Tool Integrity Checks Stop: A Field-Level Comparison and a Minimal Lockfile-Depth Fix

**Author:** Ria Banerjee
**Status:** Complete draft — all four experiments run and reproducible, abstract and conclusion written, all citations resolved. Ready for a proofreading pass before submission.
**Competing interests:** The author is the sole developer of Tooldex, one
of the eight systems evaluated in this paper (§3, §5). No other competing
interests are declared.

---

## Abstract

Current MCP "rug-pull" defenses hash or sign a tool's *declared
interface* — name, description, input schema — not its implementation.
This paper audits where eight currently-deployed or currently-proposed
defenses stop, checked against each project's own source and
documentation, and then examines three further boundaries using a real
MCP reference server (Anthropic's official `filesystem` server) rather
than a constructed example. Experiment 1 shows that wire-level interface
hashing does not detect a schema-preserving behavior change, while a
full file hash does. Experiment 2 revisits an assumption made earlier in
this project: Tooldex's published `trust_store.py` already hashes a
server's entire local file tree, not only its entry point. Even so, that
hash stops at package-manager-installed dependencies by design —
mutating a real npm dependency the target server uses is not detected by
Tooldex's own code, called directly, or by a local-closure hash, but is
detected by a lockfile-depth extension that had previously been
specified but not run. Experiment 3 shows a further limit: a dormant,
threshold-gated trigger written once at deployment and never modified
afterward is not visible to any static hash, since nothing on disk
changes; comparing a tool's repeated output against a canary baseline
does detect it. A fourth experiment combines all three mutations against
one static-plus-canary architecture, which detects all three cases where
neither layer alone does. All four experiments are reproducible via
Docker or a plain Python/Node toolchain. The result is a specific account
of where these integrity checks stop, along with a minimal extension
that closes part of that gap and a remaining boundary the extension does
not close.

---

## 1. Introduction

Large language models (LLMs) are increasingly deployed as agentic systems
that must act beyond the boundaries of their training data. Benchmark
studies demonstrate this directly: LLMs invoke external tools mid-task
and execute code to do so, with measurable gains in task performance
from each additional turn of tool use
([Wang et al., "MINT: Evaluating LLMs in Multi-turn Interaction with
Tools and Language Feedback"](https://arxiv.org/abs/2309.10691), arXiv
2309.10691), and tool-augmented systems more broadly extend this pattern
to structured databases and web search
([Qu et al., "Tool Learning with Large Language Models: A
Survey"](https://arxiv.org/abs/2405.17935), arXiv 2405.17935). Beyond
such general-purpose tools, agents are also
increasingly connected to an organization's own proprietary data: the
Model Context Protocol (MCP) has become a common substrate for this,
standardizing how an AI application connects to external tools and data
sources and providing "secure, two-way connections between [an
organization's] data sources and AI-powered tools" — including "the
systems where data lives, including content repositories, business
tools, and development environments"
([Anthropic, 2024](https://www.anthropic.com/news/model-context-protocol)).
MCP follows a host–client–server architecture in which an AI application
(the *host*) opens a dedicated *client* connection to each *server* it
uses; a server can run locally as a subprocess on the same machine — the
common case for a filesystem or local-database tool, reached over
`stdio` — or remotely as a hosted service reached over HTTP, so a given
server may be operated by a large cloud provider or by a single
individual or small team running their own script
([Model Context Protocol, 2026](https://modelcontextprotocol.io/docs/concepts/architecture)).
Regardless of who operates it or how it is reached, a server exposes each
of its capabilities to the client as a *tool*, described only by a name,
a natural-language description, and a JSON input schema; the client
never receives the tool's underlying implementation, only this declared
interface ([Model Context Protocol, 2026](https://modelcontextprotocol.io/docs/concepts/architecture)).
A client approves a tool once, based on that interface, and then trusts
it indefinitely: "Standard MCP Clients, once a tool is 'approved' ...,
typically do not re-fetch and re-verify the tool's complete definition
(including its schema or a cryptographic hash) on every subsequent
invocation" (ETDI, §III-B, arXiv 2506.01333).

This combination — rich natural-language metadata sitting directly in an
agent's decision loop, and a trust decision made once and never
revisited — has made MCP the subject of active, rapidly growing security
research, including a systematization-of-knowledge effort aiming "to
provide a comprehensive taxonomy of risks in the MCP ecosystem"
([arXiv 2512.08290](https://arxiv.org/abs/2512.08290)). Named attack
classes include: *tool poisoning*, where an adversary embeds malicious
instructions directly in a tool's description or metadata so that they
enter the agent's context at registration time, before any tool actually
executes — first demonstrated by [Invariant
Labs](https://invariantlabs.ai/blog/mcp-security-notification-tool-poisoning-attacks)
(April 2025) and since studied at benchmark scale
([MCPTox](https://arxiv.org/abs/2508.14925), arXiv 2508.14925);
*indirect prompt injection*, where adversarial instructions are embedded
in external content a tool later retrieves — a document, a web page, a
database record — rather than in the tool definition itself, a general
LLM-application vulnerability introduced by [Greshake et
al.](https://arxiv.org/abs/2302.12173) (arXiv 2302.12173) that later work
demonstrates applies directly to MCP servers
([arXiv 2609.10854](https://arxiv.org/abs/2609.10854)); *tool shadowing*,
where a malicious server's tool description injects instructions that
alter how the agent behaves toward a different, already-trusted tool —
not by mimicking that tool's name, but by adding behavior-overriding text
the model reads alongside it — likewise first demonstrated by [Invariant
Labs](https://invariantlabs.ai/blog/mcp-security-notification-tool-poisoning-attacks)
in the same disclosure and since analyzed more generally as
descriptor-level manipulation
([arXiv 2512.06556](https://arxiv.org/abs/2512.06556)); *OAuth and token
theft*, where an agent reads and exposes credentials accessible to its
tools — locally cached API keys and secrets
([Radosevich and Halloran, "MCP Safety
Audit"](https://arxiv.org/abs/2504.03767), arXiv 2504.03767), or, in
OAuth-based deployments, an access token obtained after a malicious
server completes what looks like a normal authorization flow — a risk
the protocol's own specification names as "Token Theft" and the
"Confused Deputy Problem"
([Model Context Protocol, "Authorization Security
Considerations"](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization/security-considerations))
and which Alibaba Cloud's security team demonstrated against several
major MCP clients
([GitHub issue #544](https://github.com/modelcontextprotocol/modelcontextprotocol/issues/544),
May 2025); and *over-permission*, where a tool or agent is granted, or
induced into using, broader access than its task requires
([OWASP MCP02:2025 – Privilege Escalation via Scope
Creep](https://owasp.org/www-project-mcp-top-10/2025/MCP02-2025%E2%80%93Privilege-Escalation-via-Scope-Creep);
[arXiv 2507.06250](https://arxiv.org/abs/2507.06250)). This paper is
concerned with a sixth class, distinct from all five above in *when* the
compromise happens: the **rug pull**, in which a tool behaves as declared
at the moment a client approves it, and only later — after that approval,
with no further action from the client — starts behaving differently,
while its declared interface stays exactly as it was. The term itself
was first used for MCP by [Invariant
Labs](https://invariantlabs.ai/blog/mcp-security-notification-tool-poisoning-attacks)
in the same April 2025 disclosure that named tool poisoning and tool
shadowing — "the package or server-based architecture of MCP allows for
*rug pulls* - where a malicious server can change the tool description
after the client has already approved it" — two months before ETDI, the
first paper to propose a formal defense against it, adopted the same
name (arXiv 2506.01333). Rug pull is named explicitly in OWASP's MCP Top
10
([MCP04:2025 – Software Supply Chain Attacks & Dependency
Tampering](https://owasp.org/www-project-mcp-top-10/2025/MCP04-2025%E2%80%93Software-Supply-Chain-Attacks&Dependency-Tampering)),
in Microsoft's Zero Trust attack-technique catalog
(["Rug-Pull Attack (Agent / MCP
Server)"](https://learn.microsoft.com/en-us/security/zero-trust/catalog-ai-attack-techniques/rug-pull-attack),
dated July 2026), and in ETDI (arXiv 2506.01333), and is the
acknowledged, self-reported limitation of
at least three independent, actively-maintained defense projects (§3).

Despite this attention, existing MCP security research is mostly
attack-centric: it shows how an attack works, not where a defense
stops. A defense-*placement* taxonomy makes this point directly, finding
that current defenses "concentrate on tool-adjacent protections, while
important threats involving host orchestration, transport assumptions,
and registry/supply-chain mechanisms remain comparatively underdefended"
([MCP-DPT](https://arxiv.org/pdf/2604.07551), arXiv 2604.07551). That
taxonomy maps *where* a defense sits, not *what* it checks. This paper
does the latter, narrowly, for rug pull. Every experiment below runs
against a real, actively-maintained MCP reference server — Anthropic's
own official `filesystem` server — not a constructed example.

First, we audit eight real defenses field by field, to see exactly what
each one covers (§3). Second, we compare wire hash against file hash:
wire hash misses a schema-preserving behavior change; file hash catches
it (§4, Gap 1). Third, we compare a local-closure hash against a
lockfile-depth hash: the local-closure hash misses a real dependency
compromise; the lockfile-depth extension catches it (§5, Gap 2). Fourth,
we compare a static hash against a canary check — repeating the same
tool call and comparing each response to an established baseline: no
static hash, however complete, catches a dormant trigger that never
touches disk; the canary check does (§6, Gap 3). A combined experiment
then reruns all three
mutations together against one static-and-canary check, and catches
every case (§6).

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

Kept here deliberately, ahead of the threat model, so neither reading is
available as a misreading by the time a reviewer reaches it.

---

## 2. Threat model

A tool's implementation can change without its interface changing through
several ordinary, already-observed channels — not only "an attacker
breaks into your laptop":

- **Compromised transitive dependency.** The entry-point file is
  untouched; a package it imports gets a malicious version pushed to
  PyPI/npm. Real precedent: **Clinejection** (17 February 2026) — a
  compromised npm publish token was used to push a malicious `cline@2.3.0`
  to the npm registry, adding a `postinstall` script that silently
  installed an unauthorized second AI agent on an estimated ~4,000
  developer machines before the package was deprecated roughly eight
  hours later ([Cloud Security Alliance research
  note](https://labs.cloudsecurityalliance.org/research/csa-research-note-clinejection-prompt-injection-cicd-cache-p/);
  [Snyk](https://snyk.io/blog/cline-supply-chain-attack-prompt-injection-github-actions/)).
  §5 demonstrates the exact mechanism this describes, not just its
  plausibility: a real npm dependency (`minimatch`) of a real reference
  server, mutated in place, invisible to wire hashing and to Tooldex's
  real, current `trust_store.py` alike.
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

**A tool deliberately left out, and why.** Invariant Labs' MCP-Scan is
widely described secondhand (its own docs included) as offering "Tool
Pinning... via tool hashing" for rug-pull detection, which would put it
in this table. Checking that claim directly, the way every row above was
checked, does not confirm it: `mcp-scan`'s PyPI listing states the
package "has been renamed to snyk-agent-scan" and now forwards to it —
the same `snyk/agent-scan` repository already cited in §2 for its
capability-expansion proposal and release-transition measurement, not a
different project. Installing the current successor package
(`snyk-agent-scan` 0.6.4) and searching its actual source for any
rug-pull- or tool-pinning-specific hashing code path turns up nothing
under that name. Rather than include a row built on a secondhand claim
this project's own standard couldn't verify against real, current source,
it's excluded — itself a small illustration of how quickly documentation
and implementation drift apart even for the well-established projects in
this exact space.

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

**Reading:** wire-level hashing — what most of the eight existing
defenses catalogued in §3 rely on — does not detect the change, on
Anthropic's own real, popular reference implementation, not a hand-built
example. File hashing
does. This confirms, mechanically rather than by assertion and on real
production code, the limitation that mcpseal, mcp-pin, and
hardened-mcp-server each already state about themselves in their own
documentation.

See `scripts/experiment_1/README.md` for the exact mutation and run
instructions; see §5 for an ESM-vs-CommonJS resolution detail worth
knowing before extending this mutation approach to a different tool.

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
  level deeper — expected **changed**. This extension was previously left
  specified-but-not-built; this is the first time it's actually run.
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
hash-of-hashes) and one canary layer, under a single combined decision
rule — flag if either layer moves. Not a new experiment; the same
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
- **The field-level audit (§3) is a snapshot of fast-moving, mostly
  single-maintainer projects, not a stable literature.** §3's own
  MCP-Scan finding — secondary sources describe a hashing-based "Tool
  Pinning" feature that could not be confirmed in the current, renamed
  successor package's actual source — is direct evidence that this
  table can go stale in either direction (a tool gaining coverage, or
  documentation outliving a feature) faster than a typical citation.
  Treat §3 as accurate as of the dates in the References list, not as a
  permanent characterization of any of these projects.

---

## 9. Conclusion

Every current MCP rug-pull defense stops at the tool's declared
interface; this paper locates three further, nested boundaries and
demonstrates each mechanically, on the same real reference server, rather
than asserting them. Gap 1 shows wire-level interface hashing misses a
schema-preserving behavior change that a full file hash catches. Locating
Gap 2 precisely required correcting an assumption this project started
with: Tooldex's real, published `trust_store.py` is not entry-point-only,
as first assumed, but already hashes a server's whole local file tree —
confirmed by reading its actual source rather than its documentation.
What it still misses, demonstrated here against a real npm dependency and
Tooldex's real code rather than a reimplementation, is a compromise
delivered specifically through a package-manager-installed dependency —
closed by a minimal lockfile-depth extension that was previously
specified but, until this work, never actually run. Gap 3 shows a further
limit that no static hash can cross by construction, however complete:
a dormant, threshold-gated trigger written once at deployment and never
touched again leaves nothing on disk for any hash to ever see change,
and is caught only by comparing a tool's own repeated output against a
canary baseline. A fourth, combined experiment shows a unified
static-plus-canary architecture catching every one of these cases where
neither layer catches all of them alone. What this paper does not
attempt — deliberately, per §7.3 — is a population-scale measurement of
how many real MCP deployments each gap reaches; that remains open for
separate work, building on this paper's mechanism rather than competing
with the ecosystem-scale census work already cited here.

---

## References

URLs below were all directly verified (fetched/read primary source), not
taken from secondary summaries.

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
14. hardened-mcp-server (jkelly-dev1) — repository, direct doc quote in §3 —
    https://github.com/jkelly-dev1/hardened-mcp-server
15. mcpseal (confuseddude) — repository, direct doc quote in §3 —
    https://github.com/confuseddude/mcpseal
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
23. "MCP-DPT: A Defense-Placement Taxonomy and Coverage Analysis for Model
    Context Protocol Security", cited in §1 —
    https://arxiv.org/pdf/2604.07551
24. Cloud Security Alliance, "Clinejection: Prompt Injection in GitHub
    Issue Titles Enables CI/CD Cache Poisoning and Supply Chain
    Compromise", cited in §2 —
    https://labs.cloudsecurityalliance.org/research/csa-research-note-clinejection-prompt-injection-cicd-cache-p/
25. Snyk, "How 'Clinejection' Turned an AI Bot into a Supply Chain
    Attack", corroborating account of the same incident, cited in §2 —
    https://snyk.io/blog/cline-supply-chain-attack-prompt-injection-github-actions/
26. `mcp-scan` / `snyk-agent-scan`, PyPI package pages — primary-source
    basis for the exclusion decision in §3 —
    https://pypi.org/project/mcp-scan/ and
    https://pypi.org/project/snyk-agent-scan/
27. Qu et al., "Tool Learning with Large Language Models: A Survey",
    cited in §1 — https://arxiv.org/abs/2405.17935
28. Wang et al., "MINT: Evaluating LLMs in Multi-turn Interaction with
    Tools and Language Feedback" (ICLR 2024), cited in §1 —
    https://arxiv.org/abs/2309.10691
29. Anthropic, "Introducing the Model Context Protocol" (announcement),
    cited in §1 — https://www.anthropic.com/news/model-context-protocol
30. Model Context Protocol, "Architecture overview" (specification docs,
    protocol revision 2026-07-28), cited in §1 —
    https://modelcontextprotocol.io/docs/concepts/architecture
31. "Systematization of Knowledge: Security and Safety in the Model
    Context Protocol Ecosystem", cited in §1 —
    https://arxiv.org/abs/2512.08290
32. Invariant Labs, "MCP Security Notification: Tool Poisoning Attacks"
    (1 April 2025) — origin of both "tool poisoning" and "tool
    shadowing" as named MCP attacks, cited in §1 —
    https://invariantlabs.ai/blog/mcp-security-notification-tool-poisoning-attacks
33. "MCPTox: A Benchmark for Tool Poisoning Attack on Real-World MCP
    Servers", cited in §1 — https://arxiv.org/abs/2508.14925
34. Greshake et al., "Not what you've signed up for: Compromising
    Real-World LLM-Integrated Applications with Indirect Prompt
    Injection" — origin of "indirect prompt injection" (general LLM
    context, predates MCP), cited in §1 —
    https://arxiv.org/abs/2302.12173
35. "No-Box Vulnerability Analysis: Description-only Detection of
    Indirect Prompt Injection Vulnerabilities in MCP Servers", cited in
    §1 — https://arxiv.org/abs/2609.10854
36. "Semantic Attacks on Tool-Augmented LLMs: Securing the Model Context
    Protocol Against Descriptor-Level Manipulation", cited in §1 —
    https://arxiv.org/abs/2512.06556
37. Radosevich and Halloran, "MCP Safety Audit: LLMs with the Model
    Context Protocol Allow Major Security Exploits", cited in §1 —
    https://arxiv.org/abs/2504.03767
38. Model Context Protocol, "Authorization Security Considerations"
    (specification docs, protocol revision 2026-07-28) — defines "Token
    Theft" and the "Confused Deputy Problem", cited in §1 —
    https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization/security-considerations
39. AlibabaCloudSecurity, GitHub issue #544 on
    `modelcontextprotocol/modelcontextprotocol`, "The MCP protocol
    exhibits insufficient security design, which increases the risk of
    widespread phishing attacks" (18 May 2025) — first disclosed OAuth
    access-token theft exploit against major MCP clients, cited in §1 —
    https://github.com/modelcontextprotocol/modelcontextprotocol/issues/544
40. OWASP MCP Top 10, MCP02:2025 – Privilege Escalation via Scope Creep,
    cited in §1 —
    https://owasp.org/www-project-mcp-top-10/2025/MCP02-2025%E2%80%93Privilege-Escalation-via-Scope-Creep
41. "We Urgently Need Privilege Management in MCP: A Measurement of API
    Usage in MCP Ecosystems", cited in §1 —
    https://arxiv.org/abs/2507.06250
