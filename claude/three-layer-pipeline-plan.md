# Three-layer MCP integrity pipeline: wire hash + file/closure hash + deterministic canary

Status as of 2026-09-19. This supersedes the Gap 1/Gap 2-only framing in
`preprint.md` — not by discarding it, but by extending it with a third
layer that reaches what Gap 1/Gap 2 explicitly could not (the npx/uvx
majority with no local file to hash at all). `preprint.md` itself is not
yet rewritten to this framing; this file is the current plan of record
until that rewrite happens.

## 1. Research question

Every current MCP integrity/rug-pull defense operates at exactly one
layer — either the declared interface (what ETDI, mcpseal,
hardened-mcp-server, mcp-pin, Vercel's `detectToolDrift`, and MCP Manager
all hash or sign) or, in the single strongest deployed case (Tooldex), the
entry-point file's local directory tree. Each layer has a precise,
verifiable boundary past which it cannot see anything, and no existing
defense combines complementary layers to cover the full space of real MCP
deployments — including the majority that are launched via `npx`/`uvx`
and have no stable local file at all.

**Can a fully deterministic (no LLM, no learned/statistical baseline)
pipeline — combining interface hashing, dependency-closure file hashing,
and fixed-input canary probing — be built and demonstrated such that the
three layers together cover integrity verification across the full real
deployment surface, and precisely where does each individual layer's
coverage start and stop?**

## 2. What this paper aims to do

1. Precisely audit exactly what every real, currently-deployed MCP
   integrity mechanism covers and where each one stops (field-level, from
   primary sources — already done, `preprint.md` §3).
2. Demonstrate — not assert — the exact boundary of each individual layer
   via reproducible mutation experiments, building a "boundary staircase"
   where each experiment shows one layer's blind spot and the next layer
   catching it.
3. Propose and build a minimal, working, deterministic three-layer
   reference pipeline, and demonstrate its combined coverage against a
   coverage matrix no single existing defense achieves.
4. State plainly, with its own dedicated experiment, where even the
   combined pipeline's coverage stops (canary evasion) — the same
   precision-about-boundaries standard applied to every other claim in
   this project.

## 3. How it aims to do that

- **Field-level audit** (done): 7-8 real defenses, each verified by
  reading primary source/docs directly, not paraphrased.
- **A staged sequence of mutation experiments**, each isolating one
  layer's blind spot:
  - Wire hash's blind spot → caught by file hash (Gap 1, done).
  - Entry-point-only file hash's blind spot → caught by whole-closure
    hash (Gap 2, designed, not run).
  - Every hash-based layer's structural blind spot (no local file exists
    at all) → caught by canary probing (new).
  - Canary probing's own blind spot (evasion) → stated honestly, not
    solved (new, deliberately a "miss" result, not a "catch").
- **A combination experiment**: run all three layers together across a
  small set of representative deployment shapes (single-file local
  script, multi-file/dependency local script, npx-style unpinnable
  package) and produce a coverage matrix showing which layer(s) catch
  which mutation in which deployment shape — the paper's central results
  artifact.
- **Deterministic judging design for the canary layer** — field-level
  volatility classification with derivation/bound-checking for
  partially-volatile output (e.g. `get_current_time`'s `day_of_week` is
  derivable from its `datetime`, not independently volatile), and a
  canary-token pattern for fully generative output — engineered, not
  hand-waved. LLM-backed/fully-generative tool judging is explicitly
  deferred to future work (§7), not claimed as solved.

## 4. Experiments, in detail

| # | Name | Setup | Layers compared | Deployment shape |
|---|---|---|---|---|
| 1 | **Gap 1** (done) | `echo_server.py`, body-only mutation, name/description/schema untouched | wire hash vs. file hash | single-file local script |
| 2 | **Gap 2** (designed, not run) | entry point imports a module resolved from *outside* its local directory tree (genuinely external dependency, not a sibling file); mutate only the external module | entry-point-only file hash (Tooldex's real `trust_store.py`, called directly — not reimplemented) vs. whole-closure hash | multi-file local script with an external dependency |
| 3 | **Canary reaches the unpinnable majority** (new) | a server with no stable local file at all (a real `npx`-style package-registry launch, or a faithful stand-in — code re-resolved externally on each run) | wire hash (fails to detect — interface untouched) and file hash (**cannot even be computed** — no file to hash) vs. canary probe with a planted fixture and deterministic judge | package-registry-launched server, no local file |
| 4 | **Canary's own boundary** (new, a deliberate "miss") | mutation that detects the fixed canary input specifically (sandbox/canary-evasion pattern) and behaves maliciously only for real, non-canary traffic | canary probe — **expected to miss this one**, stated as the pipeline's own honest limit | any deployment shape; the point is the evasion technique, not the shape |
| 5 | **Combination / coverage matrix** (new) | all three layers run together against the three deployment shapes from experiments 1-3 | wire + file/closure + canary, combined | single-file, multi-file/dependency, unpinnable-package — all three |

Each of 1-4 reuses the same harness pattern already proven in experiment 1
(snapshot v1 → probe all applicable signals → mutate → probe again →
compare → restore) — experiment 5 is the aggregation of that pattern
across shapes, not new machinery.

## 5. Expected results

- **Experiment 1**: wire hash unchanged, file hash changed, real output
  changed. *(Already confirmed — real run, not hypothetical.)*
- **Experiment 2**: wire hash unchanged, entry-point-only file hash
  **unchanged** (the point), whole-closure hash changed, real output
  changed.
- **Experiment 3**: wire hash unchanged, file hash **not applicable** (no
  file exists to hash), canary judge flags a mismatch, real output
  changed.
- **Experiment 4**: all signals show detection **except** canary — this
  is the one row in the results table where the pipeline is expected to
  fail, reported as a finding, not hidden.
- **Experiment 5**: a coverage matrix (rows = deployment shape, columns =
  layer) where no single column is `✓` for every row, but the combined
  pipeline (any-column-✓ per row) is `✓` for every row except the
  evasion case from experiment 4 — the central table of the paper.

## 6. Known limitations

- **Canary probing is evadable in a way hashing is not — but the risk is
  bounded to exactly where nothing better is available.** A
  sufficiently sophisticated mutation can detect it is being tested
  (recognize a fixed canary input) and behave normally only for that
  input; hashing checks bytes, not behavior, and cannot be fooled this
  way. This is experiment 4, a demonstrated miss, not a footnote. The
  bound: wherever a local file exists to hash, the file/closure hash
  layer is immune to this evasion by construction (any code change,
  conditional or not, changes the file's bytes) — so canary evasion is a
  live residual risk only for the unpinnable `npx`/`uvx` majority, where
  canary is the sole available layer regardless. Partial, non-complete
  mitigations worth noting: randomizing canary inputs instead of reusing
  one fixture, and interleaving canary calls among real traffic so they
  are not trivially fingerprinted — neither eliminates the risk against a
  sufficiently determined attacker.
- **Deterministic judging needs per-tool engineering.** Field-volatility
  classification and fixture design don't automatically generalize to an
  arbitrary new tool without setup work — this doesn't scale
  unsupervised the way a generic hash does.
- **Side-effecting tools narrow eligibility, but by less than "read-only
  only."** The real boundary is not read vs. write — it's whether the
  operation can be redirected at a resource you own and is reversible or
  absorbable. Most write tools qualify via a create-verify-cleanup
  pattern (a canary file path, a canary mailbox, a canary repo, a rolled-
  back transaction) — standard practice already used safely in CI
  integration testing. The genuinely excluded case is narrower and more
  specific: operations that are both irreversible *and* externally
  targeted with no ownable substitute (an SMS to a caller-supplied real
  phone number, an irreversible financial transfer, a post to a real
  production account with no test account available). This layer's
  eligible scope is "read-only, or safely redirectable/reversible
  write" — not "read-only."
- **No coverage claim for LLM-backed/fully-generative tools** — deferred
  to future work (§7) as deterministic judging for generative-output
  subjects, not as an LLM-based judge (that would collide with
  MCPShield's mechanism, which this project deliberately avoids for
  auditability/adversarial-robustness reasons — see references).
- **Small-N, hand-verified case studies, not a population measurement.**
  Deliberate scope choice, consistent with the rest of the project.
- **Single implementer, single pass**, no independent replication.
- **No incidence-rate claim.** Silent, interface-preserving changes are
  by construction invisible to every current detection method, so no
  real-world attack frequency is derivable from existing data — this
  paper is about detection coverage, not exploitation prevalence.

## 7. Conclusions (draft shape, not yet written)

Every current MCP integrity mechanism operates at exactly one layer and
stops at a precise, previously-unstated boundary; no existing defense
combines layers to reach the full deployment surface. This paper locates
each boundary precisely (via a verified field-level audit and a staged
sequence of mutation experiments), and demonstrates — not just proposes —
a minimal, deterministic three-layer pipeline that reaches further than
any single existing layer, while stating plainly, with its own dedicated
experiment, exactly where even the combined pipeline still stops
(canary evasion, generative-tool judging). The contribution is precision
about exact boundaries at every layer, not a claim of having solved MCP
tool integrity generally.

## 8. Future work

Narrowed to the two strongest candidates — most directly tied to a
limitation named in §6, highest real-world stakes, clearest concrete
technical direction. (Others considered and cut: extending
redirectable-write probing per tool type, the irreversible-case
substitute, reference-server validation for experiments 3-5, and
population-scale deployment-shape measurement — each real, but either
leftover engineering scope rather than a research question, or more a
sibling paper than an extension of this one's own mechanism.)

- **Canary-evasion countermeasures, scoped to the unpinnable majority
  specifically** — randomizing canary inputs, or interleaving canary
  traffic indistinguishably among real traffic, so a mutation cannot
  reliably detect it's being tested. This is the residual risk on the
  *only* layer that reaches the `npx`/`uvx` majority (wherever a local
  file exists, the file/closure hash layer is already evasion-immune by
  construction), so it carries the highest real-world stakes of anything
  in this project. A genuine, open adversarial research question —
  randomization vs. fingerprinting is a real cat-and-mouse problem, not
  just an implementation detail.
- **Deterministic judging for generative-output tools** (renamed from
  "LLM-backed tool judging" to remove an ambiguity caught mid-session —
  this is about judging tools whose *output* is generative, using a
  judge that stays deterministic, not about adding an LLM as the judge;
  the latter would collide with MCPShield's own mechanism, which this
  project deliberately avoids). Candidate directions: forcing
  determinism via temperature=0/fixed-seed where the tool exposes it;
  canary-token presence/absence checks where it doesn't. Directly closes
  the limitation named in §6, with a concrete technical path already
  sketched.

## References

1. ETDI: Mitigating Tool Squatting and Rug Pull Attacks in MCP — arXiv 2506.01333
2. mcpseal (confuseddude) — github.com/confuseddude/mcpseal
3. hardened-mcp-server (jkelly-dev1) — github.com/jkelly-dev1/hardened-mcp-server
4. mcp-pin / Plumbline (GautamTalksDev) — github.com/GautamTalksDev/mcp-pin,
   github.com/GautamTalksDev/Plumbline
5. Vercel AI SDK tool-drift detection (`detectToolDrift`, `ai@7.0.19`) —
   newreleases.io/project/github/vercel/ai/release/ai@7.0.19
6. MCP Manager, Feature Governance — docs.mcpmanager.ai/security/feature-governance
7. Microsoft Agent Package Manager (APM) — microsoft.github.io/apm,
   github.com/microsoft/apm
8. MCP-DPT: A Defense-Placement Taxonomy and Coverage Analysis for MCP
   Security — arXiv 2604.07551
9. MCPShield: A Security Cognition Layer for Adaptive Trust Calibration in
   MCP Agents — arXiv 2602.14281
10. "Beyond Detection: Autonomous Anomaly Remediation for MCP Against Tool
    Poisoning Attacks" (MCPFixGen) — ACM Web Conference 2026,
    doi.org/10.1145/3774904.3792400
11. ARMO, "AI Workload Baseline and Drift Detection: Defining 'Normal'
    Agent Behavior" — armosec.io/blog/ai-workload-baseline-drift-detection
12. MCP Trust & Tool Drift Monitor (Apify, fascinating_lentil) —
    apify.com/fascinating_lentil/mcp-trust-rug-pull-monitor
13. cisco-open/mcptoolkit-test — github.com/cisco-open/mcptoolkit-test
14. "Same Name, Different Server: A Security Census of Silent Drift in the
    MCP Ecosystem" — arXiv 2609.14119
15. OWASP MCP Top 10, MCP04:2025 – Software Supply Chain Attacks &
    Dependency Tampering
16. Microsoft Learn, Rug-Pull Attack (Agent / MCP Server) — Zero Trust
    attack-technique catalog
17. "Pinning Is Futile: You Need More Than Local Dependency Versioning to
    Defend against Supply Chain Attacks" — arXiv 2502.06662 (CMU, FSE'25)

> **TODO**: exact citable source for the Clinejection npm-package
> incident (currently referenced from memory, carried over from
> `preprint.md`'s existing TODO).
