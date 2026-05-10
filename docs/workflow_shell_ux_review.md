# Workflow Shell UX Review

Date: 2026-05-10

Scope: hands-on review of the shared Tauri workflow shell against a disposable Rust SQLite database, seeded with realistic Today, Capture, Process, and Settings data. Updated after the Weekly Review workflow was added as the fifth top-level path.

## Findings

- The workflow shape is the right direction. Today, Capture, Process, Review, and Settings are easier to reason about than the earlier single dashboard.
- Capture is currently the strongest workflow. It has one input, one decision, and enough confirmation. Keep the phone version this sparse.
- Today is coherent with realistic data: One Thing, Frog, current/next block, daily context, today tasks, weekly projects, and blocks all line up. The hands-on execution pass verified complete, reopen, visible completed state, and reversible action feedback in the macOS shell and iOS simulator.
- Process had a mismatch: it promised "one item at a time" while exposing the full inbox queue with actions. The shell now exposes only the active inbox item as actionable, with the position badge preserving queue context.
- Process still has the densest remaining UX risk, but the guided Task / Project / Waiting On form is now split into progressive Type, Describe, and Details/Save steps instead of one dense panel.
- iOS simulator review found Tauri's phone WebView using a wider layout viewport than expected. The mobile breakpoint now covers that viewport, prevents horizontal overflow, puts the decision queue before the stats card on phone-sized layouts, and keeps Settings inputs from triggering iOS focus zoom.
- Settings is clear enough for the current Mac and simulator loopback path. The guidance around loopback vs LAN/VPN is useful and should be verified on a physical iPhone once signing is ready.
- Action feedback had two misleading persistence bugs: old success/undo messages survived reconnecting to another server/database, and task lifecycle feedback followed the user into unrelated workflows. Reconnects and workflow switches now clear stale feedback.
- Review now has the minimum useful weekly loop: focus counts, active project toggles, due resurfacing move-to-week, and completed-task cleanup. The main remaining risk is product fit, not plumbing; it needs a real weekly review pass before adding notes, calendars, or long-range boards.

## Completed Follow-Up Slice: Process

Make Process feel deliberately mobile:

- Kept one active item at a time.
- Split guided clarification into small steps: type, title/notes, only relevant fields, save.
- Kept route/recycle undo visible and reversible.
- Verified the progressive Type -> Describe -> Plan path in the iPhone 17 Pro simulator against disposable Rust data.
- Moved the actionable decision queue above inbox stats on mobile so Process opens on work, not telemetry.

## Completed Follow-Up Slice: Today Tasks

Make Today tasks actionable:

- Added Complete/Reopen controls to Today task rows.
- Kept completed Today tasks visible so mistaken completions can be reversed from the row itself.
- Reused action feedback for the opposite lifecycle action where the API supports it.
- Kept completed rows visually quieter without changing the subtler rounded-edge style.

## Completed Follow-Up Slice: Today Execution UX Review

Check whether Today supports real execution on macOS and iOS simulator:

- Verified complete/reopen on seeded Today tasks from the shared shell.
- Verified capture/process interruptions do not break Today state.
- Fixed action feedback so it clears when the user changes workflow.
- Fixed the iOS Settings viewport and input focus behavior found during the simulator pass.
- Kept the current responsive shell as good enough for the next product slice; a deeper phone-native Today redesign can wait until physical iPhone testing.

## Completed Follow-Up Slice: Weekly Review

Add the first review loop without turning it into a second planning app:

- Added Review as the fifth top-level workflow.
- Loaded weekly review data from the Rust API alongside bootstrap, inbox, and project data.
- Rendered work/personal focus counts, current weekly projects, candidate project toggles, due resurfacing tasks, and completed cleanup.
- Wired focus toggle, move-to-week, archive, restore, and refresh actions.
- Kept the layout within the existing neon shell and the restrained button-radius style.

## Recommended Next Slice

Move from simulator confidence to a real-device connection pass if signing is available: install on a physical iPhone, point it at the Mac mini/LAN server URL, and verify Today, Capture, Process, Review, and Settings against the same database. If signing is not ready, run a hands-on Weekly Review UX pass on macOS with real data before adding persisted review notes, week calendar planning, or long-range boards.
