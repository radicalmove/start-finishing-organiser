# SFO Native Park Reminders Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `Park until` items schedule native device notifications so SFO starts replacing the Apple Reminders/Trello snooze workflow.

**Architecture:** Keep the first slice deliberately small: reuse existing `tasks.parked_until` as the reminder time and schedule local notifications from the Tauri shell after connect/refresh. The server remains the source of truth; each device schedules its own local notification when it sees future parked items.

**Tech Stack:** Rust/Tauri v2 notification plugin, static launcher JavaScript, existing `/api/v1/inbox/containers` parked-item payloads, Node tests, Cargo checks.

---

### Task 1: Native Notification Scaffold

**Files:**
- Modify: `src-tauri/Cargo.toml`
- Modify: `src-tauri/src/lib.rs`
- Modify: `src-tauri/capabilities/default.json`
- Test: `src-tauri/launcher/mobile-scaffold.test.mjs`

- [ ] **Step 1: Write the failing scaffold test**

Assert that the Tauri notification plugin is declared, initialized, and permitted.

- [ ] **Step 2: Run the test to verify it fails**

Run: `node --test src-tauri/launcher/mobile-scaffold.test.mjs`

- [ ] **Step 3: Add the plugin scaffold**

Add `tauri-plugin-notification`, initialize it in `lib.rs`, and grant `notification:default`.

- [ ] **Step 4: Re-run the scaffold test**

Run: `node --test src-tauri/launcher/mobile-scaffold.test.mjs`

### Task 2: Parked Item Notification Scheduler

**Files:**
- Modify: `src-tauri/launcher/client.js`
- Modify: `src-tauri/launcher/client.test.mjs`
- Modify: `src-tauri/launcher/launcher.js`

- [ ] **Step 1: Write failing scheduler tests**

Cover deterministic notification IDs, future-only filtering, permission handling, and scheduling payloads.

- [ ] **Step 2: Run the scheduler tests to verify failure**

Run: `node --test src-tauri/launcher/client.test.mjs`

- [ ] **Step 3: Implement scheduler helpers**

Export helpers that turn parked tasks into Tauri notification requests and no-op safely outside Tauri.

- [ ] **Step 4: Wire scheduling after connect/refresh**

After loading inbox containers, schedule future parked reminders for the current device.

- [ ] **Step 5: Re-run launcher tests**

Run: `node --test src-tauri/launcher/*.test.mjs`

### Task 3: Verification and Device Check

**Files:**
- Modify only if tests reveal a real issue.

- [ ] **Step 1: Run Rust/Tauri checks**

Run: `cargo check --manifest-path src-tauri/Cargo.toml`

- [ ] **Step 2: Build/install on iPhone if the device is unlocked**

Run: `cargo tauri ios build --debug --target aarch64 --ci --export-method debugging`, then install the resulting app.

- [ ] **Step 3: Manual smoke test**

Park an item a few minutes into the future, keep SFO installed, and confirm the iPhone/Mac notification appears.
