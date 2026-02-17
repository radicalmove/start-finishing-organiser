# Inbox Intent and Container Strategy

Status: Approved for phased implementation  
Date: February 16, 2026  
Scope: Single-user SFO behavior redesign for inbox processing and "later" handling

---

## Implementation status (v0.732)

Phase 1 is now live with these concrete behaviors:

- Inbox header uses `Quick`, `Process`, and `Lists` (Containers, Waiting, Recycle bin) to reduce top-row clutter.
- Per-item hover actions support fast routing: `P`, `L`, `E`, `K`, and recycle bin (`D` keyboard shortcut, bin icon button).
- Quick container routes show an undo toast.
- Process flow enforces explicit intent choice for source inbox items.
- Recycle bin remains a separate destructive path; Park / Let Go remains intentional non-engagement.

---

## 1. Why this exists

This strategy addresses a recurring SFO pattern:

- too many "read/watch/listen/do later" items accumulate
- follow-through drops
- inbox and "later" states become ambiguous
- trust in the system decreases

The design goal is containment, not accumulation:

- only meaningful actionable work becomes tasks
- curiosity is captured without becoming obligation
- rest and enjoyment are protected from productivity framing
- "later" is curated, not infinite

---

## 2. Review outcome (what was agreed)

The 12-part recommendation review was accepted with targeted modifications for single-user rollout.

### Keep / Modify / Skip summary

1. Purpose: Keep, but start with new inbox processing only (no large legacy migration in v1).  
2. Problem analysis: Keep, add explicit root cause (mixed intents in one stream) and baseline metrics.  
3. Core principle: Keep, but include low-friction escape hatches (`Quick Park`, weekly-review reminder for learning only).  
4. Intent layer: Keep four intents, force decision at processing time (not raw capture time).  
5. Containers: Keep all four containers, use soft guardrails first and stricter rules later if needed.  
6. Inbox UX: Keep, with `Process` as primary action and fast secondary routing actions.  
7. Weekly review: Keep, but keep section lightweight and quick to complete.  
8. Anti-overwhelm safeguards: Keep, staged strictness (soft in v1, hard in v2 if data supports it).  
9. Phasing: Keep but reorder for fastest impact and lowest risk (inbox flow first).  
10. Evaluation: Keep, convert to explicit weekly scorecard.  
11. Non-goals: Keep as-is, plus "no broad architecture rewrite for this initiative."  
12. Closing rationale: Keep, add rule that enforcement increases only if soft guardrails fail.

---

## 3. Core rule

If something matters, it must earn a container.  
If it does not earn a container, it waits quietly or is intentionally let go.

Operationally: every processed inbox item must resolve into one explicit container state.

---

## 4. Intent model (processing-time classification)

SFO should route processed inbox items into exactly one intent:

1. `support_project`
2. `learn_explore`
3. `enjoy_recover`
4. `park_let_go`

Important rollout choice:

- Raw capture remains fast and minimal.
- Intent is mandatory when user presses `Process`.
- `unprocessed` is temporary inbox state only, not a long-term container.

---

## 5. Container behavior (approved)

## 5.1 Support a Project

Only this path can create schedulable task work.

Required in v1:

- linked active project
- at least one clarity field:
- `outcome` (what changes after doing this), or
- `deliverable` (summary/decision/next action/notes)

Guardrail in v1:

- read/watch/listen phrasing is allowed but warned and guided toward distillation.
- hard rejection can be introduced later if needed.

## 5.2 Learn / Explore

Purpose: contain curiosity without turning it into obligation.

Approved behavior:

- `Learning Backlog` exists and is hidden by default
- `Priority Picks` are the visible curated set
- temporary cap starts at 7 during early rollout, then tighten to 5 if needed
- items become picks during weekly review
- no automatic task creation from learning items

## 5.3 Enjoy / Recover

Purpose: protect restoration from work framing.

Approved behavior:

- never shown in Today or Work execution views
- never creates tasks
- stored in separate Enjoy list
- lightweight optional context tag (for example: `solo`, `with family`, `low energy`)

## 5.4 Park / Let Go

Purpose: intentional non-engagement.

Approved behavior:

- archived with explicit intentional label
- optional reason field
- no automatic resurfacing
- safety net: short undo window in v1

---

## 6. Inbox UX behavior (approved)

For each inbox item:

- primary action: `Process`
- quick secondary actions: `Learning`, `Enjoy`, `Park`
- no default direct "Create Task" action from inbox list
- keyboard shortcuts are preferred for speed (`P`, `L`, `E`, `K`)
- after quick action, show undo toast and keep focus on next item

Design intent: reduce cognitive friction while still forcing explicit containment.

---

## 7. Weekly review role (approved)

Weekly Review is the curation point for learning volume.

Required weekly elements:

1. Learning Picks panel
2. Backlog candidates panel
3. Promote/demote flow respecting picks cap
4. Optional one-click schedule actions (reading/listening blocks)
5. One short reflection question: "Still relevant this week?"

---

## 8. Anti-overwhelm safeguards (approved staged model)

V1 soft guardrails:

- warnings on vague work
- explicit container prompts
- bounded visible picks
- no silent accumulation paths

V2 hard guardrails (only if needed from measured behavior):

- stricter blocking on vague "later" task conversion
- tighter limits on visible unprocessed volume

---

## 9. Phased delivery order (approved)

1. Inbox action redesign and intent routing
2. Container model with minimal views (Learning/Enjoy/Parked)
3. Project-support quality controls (outcome/deliverable prompts)
4. Weekly review integration for curation and scheduling
5. Tightening pass (adjust caps and enforcement based on data)

Rationale: highest behavior impact with lowest regression risk.

---

## 10. Success scorecard (weekly, 4-week window)

1. Inbox load
- metric: count of inbox items older than 14 days
- target: reduce by at least 30%

2. Ambiguous drift
- metric: count of items in unprocessed/unclear state older than 7 days
- target: near zero

3. Task quality
- metric: percentage of new project-support tasks linked to project plus outcome/deliverable
- target: above 80%

4. Learning containment
- metric: Priority Picks at or under cap each week
- target: 100% compliance

5. Trust score
- metric: single-user weekly self-rating (1-5) for system clarity/trust
- target: average 4 or higher

6. Follow-through
- metric: completion rate for scheduled reading/listening blocks
- target: improving trend week-over-week

---

## 11. Explicit non-goals

- no AI prioritization engine
- no smart resurfacing heuristics
- no gamification
- no productivity scoring
- no engagement-maximization loops
- no broad architecture rewrite under this initiative

---

## 12. Implementation constraints for this initiative

- single-user optimization is intentional
- keep changes incremental and reversible
- avoid heavy refactors unless a clear hotspot blocks progress
- prioritize behavior clarity over feature breadth

---

## 13. Immediate implementation scope (Phase 1)

Phase 1 should implement only:

- inbox item actions (`Process`, `Learning`, `Enjoy`, `Park`)
- mandatory intent choice at processing step
- valid container persistence per processed item
- undo flow for quick actions
- baseline instrumentation for scorecard metrics

Out of scope for Phase 1:

- migration of all legacy later items
- strict hard blocking on all vague language
- advanced automation or AI ranking
