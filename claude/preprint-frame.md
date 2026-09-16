# Preprint frame (personal reference, not the preprint itself)

Short version of everything, for me to look at before writing the real thing.

---

## 1. Intro & background

- MCP tools have two parts: the **interface** (name, description, input schema —
  what gets shown/approved) and the **implementation** (the actual code that
  runs).
- Clients approve a tool once based on the interface, then trust it forever.
- A **"rug pull"** = the code changes later, but the interface doesn't. The
  user/agent never re-approves because nothing they can see moved.
- This is a real, named, actively-discussed threat class right now (OWASP MCP
  Top 10, multiple 2026 papers and tools) — not something I made up.

---

## 2. What exists today — reference only, NOT for the preprint

*(Keeping this here so I remember the landscape. Don't paste this section into
the actual preprint — it's homework notes, not content.)*

**Tools that defend against rug pulls, and what they actually check:**
| Tool | Checks | Misses |
|---|---|---|
| ETDI | signs the interface (OAuth) | code |
| MCP-Scan | hashes the interface | code |
| hardened-mcp-server | hashes raw wire object (best policy) | code — says so themselves |
| mcpseal | hashes interface | code — says so themselves |
| mcp-pin / Plumbline | hashes interface + logs history | code — says so themselves |
| Vercel AI SDK (`detectToolDrift`, shipped July 2026) | hashes description/schema/title | code |

**Pattern:** every single one of these hashes the *interface*, never the code.
Three of them (hardened-mcp-server, mcpseal, mcp-pin) say this out loud in
their own docs as a known limitation — but nobody had actually run a test to
prove it, or measured how often it'd even be possible to fix.

**Adjacent, not the same thing:**
- Microsoft's **Agent Package Manager (APM)** — does lockfile-based integrity
  + provenance for agent dependencies. Closest thing to "hash the code, not
  just the interface." Re-check this before claiming anything new in that
  direction.
- Academic taxonomies/benchmarks (ETDI, MCP-38, MCPTox, MCPGuard,
  MCPThreatHive, MCP-DPT, SoK paper) — name the threat, don't hash code, don't
  measure real-world reach.
- **Nobody** measures what fraction of real MCP servers even *have* a file
  that could be hashed in the first place. That's the open number.

---

## 3. What this research aims to do

Two goals only:

1. **Prove the gap is real, mechanically** (not just asserted, like everyone
   else's docs do).
2. **Measure how much of the real world the obvious fix (file-hashing) can
   even reach.**

Explicitly **not** trying to:
- invent a new defense (file-hashing already exists — Tooldex has it)
- measure how often this is actually exploited in the wild (impossible to
  measure — that's the whole point of it being silent)
- fix the npx/uvx majority (different problem, different fix, out of scope)

---

## 4. Method

**Part 1 — the mechanism demo** (`experiment_rug_pull.py` + `echo_server.py`)
- Write a toy `echo` tool. Edit only its function body (leave name/description/
  schema untouched) so it leaks `$USER`.
- Compare, before vs. after: wire hash, file hash, real tool output.
- *(Planned addition)*: same idea but mutate an **imported sibling module**
  instead of the entry-point file — shows that even file-hashing alone misses
  dependencies.

**Part 2 — the coverage measurement**
- Sample A: 423 real server entries from 240 actual `.cursor/.claude/.vscode`
  configs scraped off GitHub. Classify each by how it's launched.
- Sample B: 21,129 server entries mined out of 76,630 real MCPZoo listings.
- Report both, don't average them into one number.

---

## 5. Results (already run, reproducible)

- Wire hash: **unchanged** before/after mutation → attack invisible to every
  current defense.
- File hash: **changed** → Tooldex's approach catches it.
- Real output: **changed** (`hello` → `hello | riabanerjee`) → genuine leak,
  not simulated.
- Sample A: **13.5%** of real servers are file-hashable at all.
- Sample B: **27.4%** of real servers are file-hashable at all.
- Both samples: `npx`/`uvx` launches dominate the *un*-pinnable majority
  (43.3% / 35.4%).

---

## 6. Contributions

1. First reproducible, protocol-level proof of a gap that three independent,
   active tools already admit to but never tested.
2. Shows the "obvious fix" (file hash) is itself incomplete — misses imported
   code, not just interface.
3. First measurement (two independent sources) of how much of the real MCP
   ecosystem that fix could even reach: roughly 1-in-7 to 1-in-4.
4. Honest framing: this % is *defense coverage*, not *attack frequency* — and
   the npx/uvx majority is plausibly the more exposed group, needing a
   different fix entirely.

---

## 7. Summary

Every current MCP integrity check verifies the label on the box, not what's
inside it. Nobody had actually proven that mechanically or measured how much
it matters — this does both, honestly, without pretending the trivial fix
(file-hashing) is a full solution.
