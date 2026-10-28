# TODOS — Deferred Items (from CEO Plan Review, 2026-09-06; eng review 2026-09-06)

Follow-up items surfaced by the /plan-ceo-review of `docs/business/ROADMAP.md`
and the /plan-eng-review of the Track 0 design doc. Not in current scope; recorded so
they aren't lost.

## T-1: Launch / distribution plan (P2, effort S with CC)
- **What:** Define a minimal launch plan for ANT after Interview Track 0 ships (Show HN, r/interviews, Product Hunt, README demo GIF).
- **Why:** The master plan targets 10,000 DAU / $19k MRR but contains zero demand-generation work — building 24 weeks of supply with no demand generation is the plan's biggest strategic hole (outside voice finding #3).
- **Pros:** Makes the metrics section honest; the hybrid vertical (meeting + interview + career) needs users to matter.
- **Cons:** Distribution takes real time; can distract from building.
- **Context:** Track 0 (live interview assist) must ship and be genuinely good first — a launch of a broken stealth overlay would burn the community goodwill the open-source positioning depends on.
- **Depends on:** Track 0 complete + preflight self-check + practice mode.

## T-2: Maintenance budget policy (P1, effort S)
- **What:** Reserve ~20% of each phase's capacity for regression fixes instead of scheduling 0% maintenance across 6-12 months.
- **Why:** Codebase history is a pile of live-caught regressions (processed-column INSERT bug, agent-session dual-import, bcrypt/passlib registration breakage, missing `websockets` dep, missing `start_worker()`). A plan with zero maintenance budget is "a wish" (outside voice finding #6).
- **How to apply:** In each phase plan, count the phase in weeks and mark ~1 in 5 weeks as fix/burn-down weeks.
- **Depends on:** Nothing — adopt as policy at the Track 0 → Phase 0 transition.

## T-3: BYOK cloud-burst fallback for live assist (P3, effort M)
- **What:** When local Ollama generation exceeds ~3s (cold model, long question, heavy CPU contention), fall back to the user's own cloud API key via the existing 8-provider BYOK AI router, then revert to local.
- **Why:** Local gen measured ~650ms warm, but cold-start and CPU contention (Section 7 findings) can push past the 3-5s thinking-pause window. The user chose Approach C (local ideal architecture) without the cloud-burst element of Approach B.
- **Context:** Trigger = measured gen latency, not a config flag. Must respect the stealth spec (no unexpected network stalls). The AI Router already has race mode + fallback chain patterns to reuse.
- **Depends on:** LiveAssistService extraction (T1) so the fallback sits behind one interface.
## T-4: mac codesign fix, restore macOS release matrix (P1, effort M)
- **What:** Fix electron-builder ad-hoc signing (identity handling, framework signing) so the macOS matrix entry can be restored to `.github/workflows/release.yml` and mac artifacts publish again.
- **Why:** The mac release train has been dark since v2.2.3 (commits cb1fed2/ee5f66a/bbf4de4 removed the matrix entry). Interview Track 0's distribution depends on it — a finished overlay nobody can download is worthless.
- **Pros:** Unblocks mac distribution for Track 0 and every later release; removes the "local electron-builder only" workaround.
- **Cons:** Signing/debugging time with no user-visible feature; can be fiddly (identity null vs "-", gatekeeper, framework signing).
- **Context:** Found by the eng review distribution check (2026-09-06); the Track 0 design doc records it as a hard prerequisite for Track 0 distribution (not for development). Until fixed, Track 0 builds are verified via local electron-builder runs.
- **Depends on:** Nothing — can start anytime; must complete before Track 0 ships.
