# Workflow Shell UX Review

Date: 2026-05-09

Scope: hands-on review of the shared Tauri workflow shell against a disposable Rust SQLite database, seeded with realistic Today, Capture, Process, and Settings data.

## Findings

- The four-workflow shape is the right direction. Today, Capture, Process, and Settings are easier to reason about than the earlier single dashboard.
- Capture is currently the strongest workflow. It has one input, one decision, and enough confirmation. Keep the phone version this sparse.
- Today is coherent with realistic data: One Thing, Frog, current/next block, daily context, today tasks, weekly projects, and blocks all line up. The next Today improvements should be functional controls such as complete/reopen, not more dashboard chrome.
- Process had a mismatch: it promised "one item at a time" while exposing the full inbox queue with actions. The shell now exposes only the active inbox item as actionable, with the position badge preserving queue context.
- Process still has the densest remaining UX risk. The guided Task / Project / Waiting On form is workable on Mac, but it should become a progressive phone flow before real iPhone use.
- Settings is clear enough for the current Mac and simulator loopback path. The guidance around loopback vs LAN/VPN is useful and should be verified on a physical iPhone once signing is ready.
- Action feedback had a misleading persistence bug: old success/undo messages survived reconnecting to another server/database. Reconnects now clear stale feedback before loading data.

## Recommended Next Slice

Make Process feel deliberately mobile:

- Keep one active item at a time.
- Split guided clarification into small steps: type, title/notes, only relevant fields, save.
- Keep route/recycle undo visible and reversible.
- Add a deliberate skip/defer action only if one-item processing feels too blocking in real use.

This should happen before adding larger weekly-review or long-range planning surfaces, because Process is the workflow most likely to become annoying on iPhone if it remains desktop-shaped.
