# Where MCP Tool Integrity Checks Stop: A Field-Level Comparison and a Minimal Closure-Hash Fix

**Author:** Ria Banerjee
**Status:** Draft — sections marked `TODO` need your input/results before submission.
**Competing interests:** The author is the sole developer of Tooldex, one
of the eight systems evaluated in this paper (§3, §5). No other competing
interests are declared.

---

## Abstract

> **TODO (you):** write last, 150–200 words. Should state: (1) every current
> MCP "rug-pull" defense hashes or signs some subset of a tool's *declared
> interface*, never its implementation; (2) even the obvious fix — hashing
> the server's source file, which we demonstrate is necessary and sufficient
> against interface-preserving behavior changes — has its own boundary: it
> only covers the entry-point file, not what that file imports; (3) we give
> a field-by-field audit of seven real, currently-deployed defenses showing
> none reach the dependency closure, and a minimal reference
> implementation, extending a reproducible test harness, that does.

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
actually stops, and none of them closes the specific, narrower boundary
that remains even after you adopt the most obvious fix (hashing the
server's source file instead of its declared interface). This paper does
both:

1. A field-by-field audit of seven real, currently-deployed or
   currently-proposed MCP integrity mechanisms, showing precisely which
   fields each one covers and where each one stops (§3).
2. A reproducible demonstration that even the best of these — full
   source-file hashing — has its own uncovered boundary: it does not
   follow the file's imports (§4, §5, Gap 2).
3. A minimal reference implementation that closes that boundary by hashing
   the full dependency closure instead of a single file, and a
   demonstration that it catches what every other approach in the audit
   misses (§5).

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
  version live for ~8 hours, February 2026.
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
| **Tooldex `trust_store.py`** | full byte content of the entry-point file | On connect | **No** — entry point only; does not follow imports |
| **This work (proposed, §5)** | full byte content of entry-point file **+** all locally-resolved imports | On connect | **Yes** |

**Reading the table:** every row stops at a different boundary, but all
seven existing rows stop *before* the dependency closure. Tooldex's own
file hash — the strongest of the existing, deployed options — is
necessary but not sufficient, which is the specific, previously
unstated gap this paper closes.

> **TODO (you):** if you find a defense not in this table, verify its exact
> scope by reading primary docs/source directly (not a blog summary)
> before adding a row — that standard was applied to every row above.

---

## 4. Experiment 1 — the interface/implementation gap is real (Gap 1)

**Setup:** `mock_servers/echo_server.py`, an MCP server with a single tool
`echo(text: str) -> str`. `scripts/experiment_rug_pull.py` snapshots it,
edits only the function body (name, docstring/description, and signature
byte-for-byte unchanged) so it leaks `$USER` into the response, and
compares three signals before/after via real MCP protocol calls
(`tools/list`, `tools/call`) — not static inspection.

- **Wire hash** — sha256 of canonicalized `{name, description,
  inputSchema}` — replicates hardened-mcp-server's best-performing policy.
- **File hash** — sha256 of the script's bytes — what Tooldex pins today.
- **Real output** — an actual `tools/call("echo", {"text": "hello"})`.

**Result** (reproducible — rerun with
`uv run --no-project --python 3.14 --with mcp python3 scripts/experiment_rug_pull.py`):

```
v1 wire hash: a106160309d014fa20c1af3cffcc508933e08578db3a4a5cbaf37ff5bf009e68
v2 wire hash: a106160309d014fa20c1af3cffcc508933e08578db3a4a5cbaf37ff5bf009e68  <- UNCHANGED
v1 file hash: 8f831f7c05511dd115dac2d4e0097a3dd38ed2255ff08644ef7bb20dee2c1520
v2 file hash: c63dd65062059591d2f2d09d1c012d93b9229eb9075b9fa12b3c5e0d00abb1e7  <- CHANGED
v1 output: 'hello'
v2 output: 'hello | riabanerjee'  <- CHANGED (real leak, not simulated)
```

**Reading:** wire-level hashing — what six of the seven existing defenses
in §3 rely on — does not detect the change. File hashing does. This
confirms, mechanically rather than by assertion, the limitation that
mcpseal, mcp-pin, and hardened-mcp-server each already state about
themselves in their own documentation.

> **TODO (you):** this section's data is already final and reproducible —
> nothing to fill in here unless you want to add a second toy mutation
> variant.

---

## 5. Experiment 2 — even file hashing has a boundary (Gap 2)

**Motivation:** §3's table shows Tooldex's file hash is the strongest
*deployed* option, but it only covers the entry-point file. If the
mutation is delivered through a module that file imports rather than the
file itself, the entry-point hash is unaffected.

**Setup:**

> **TODO (you):** decide and document which of the two variants you ran:
>
> **(a) Toy variant** — split `echo_server.py` into two files
> (`echo_server.py`, which imports `echo_logic.py`). Mutate only
> `echo_logic.py`. Cleanest to build, but should be labeled explicitly as
> an isolated illustration, not evidence from a real deployed server.
>
> **(b) Real-server variant** — if you have time, find a real reference
> server (e.g. from `modelcontextprotocol/servers`) whose tool logic
> already lives in an imported helper module rather than inline in the
> entry point, and mutate that module instead. Stronger claim, more setup.

**Signals to compare** (same three as Experiment 1, **plus a fourth**):

- Wire hash — expected unchanged (same as Gap 1)
- **Entry-point-only file hash** (what Tooldex does today) — expected
  **unchanged**, since the entry-point file itself was not touched
- **Whole-closure hash** (entry point + imported module, concatenated or
  Merkle-combined) — expected **changed**
- Real output — expected changed

> **TODO (you):** run the experiment, paste the four-signal table here in
> the same format as §4. This is the load-bearing result of the paper —
> everything in §3 and §6 depends on this table actually showing what's
> predicted above.

```
[ TODO — results table goes here, same format as Experiment 1 ]

v1 wire hash:              ...
v2 wire hash:              ...   <- expect UNCHANGED
v1 entry-point file hash:  ...
v2 entry-point file hash:  ...   <- expect UNCHANGED  (this is the point)
v1 whole-closure hash:     ...
v2 whole-closure hash:     ...   <- expect CHANGED
v1 output:                 ...
v2 output:                 ...   <- expect CHANGED
```

**Reference implementation note:** the whole-closure hash does not require
new cryptography — it's `sha256(sorted(sha256(f) for f in [entry_point] +
resolved_local_imports))`, i.e. exactly the "hash of hashes" pattern
already standard practice in npm's `package-lock.json` `integrity` field
and pip's `--require-hashes` lockfiles (§6.2), applied at the point an MCP
client decides to trust a tool call rather than at package-install time
(which is where Microsoft APM applies the same pattern — see §3, APM row).

---

## 6. Discussion

### 6.1 What this does and does not claim

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
  hashing, cannot apply to them. That is a different problem needing a
  different fix (§6.3).
- **Does not claim** that closing this gap "eliminates" rug-pull risk even
  where it applies. Hashing is a *detection* mechanism; ETDI's own paper
  notes "users are unlikely to scrutinize a tool they believe they have
  already vetted" — a correctly-triggered re-approval prompt can still be
  clicked through. This paper's contribution stops at detection coverage,
  not human response to detection.

### 6.2 Why "hash of hashes," not a full Merkle tree

A full Merkle tree earns its cost when you need partial proofs (verify one
dependency without the full set) or operate at a scale where O(log n)
matters. A single MCP server's dependency count doesn't warrant that
machinery — a flat hash over the sorted set of per-file hashes gives the
same tamper-evidence property. Noting this explicitly to avoid
over-engineering a solution to a small-scale problem.

### 6.3 The population question — deliberately out of scope here

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

---

## 7. Limitations

- **Small-N, hand-verified case study, not a population measurement.**
  Deliberate, per §6.3 — not a weakness to apologize for at length, just
  to state plainly.
- **Single implementer, single pass.** No independent replication yet.
- **Toy or single-example real-server mutation** (per which variant is
  chosen in §5) — generalization to arbitrary real servers is illustrative,
  not exhaustive.
- **No adoption or effectiveness claim.** This paper does not measure
  whether any client actually implements whole-closure hashing, nor
  whether users respond correctly to a triggered re-approval prompt.

> **TODO (you):** add anything else you know is a real weakness once
> Experiment 2 is finished — reviewers trust a limitations section more
> when it's specific rather than boilerplate.

---

## 8. Conclusion

> **TODO (you):** 3–5 sentences. Suggested shape: restate the two nested
> gaps, restate that this is the first paper to locate them this
> precisely across seven real, named, currently-deployed defenses, restate
> the minimal reference fix and that it's demonstrated (not just proposed)
> to close Gap 2, and close with the population-scale question (§6.3) as
> the explicit next-paper pointer rather than something this paper
> attempts.

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

> **TODO (you):** add exact repo URLs for #14–15 if not already in
> `research-plan.md` — I have the quotes verified but should confirm the
> exact links are still on file before this goes out.
