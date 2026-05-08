# SFO Aesthetic Baseline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Apply the adaptive SFO neon identity to the Rust launcher shell so it can be reviewed visually before broader Mac/iPhone UX work.

**Architecture:** Keep the first pass CSS-only except for small launcher copy adjustments. Add one static Node test that protects the launcher from drifting back to the warm paper/moss identity.

**Tech Stack:** Static Tauri launcher HTML/CSS, Node test runner.

---

### Task 1: Guard The Launcher Aesthetic

**Files:**
- Create: `src-tauri/launcher/aesthetic-baseline.test.mjs`

- [ ] **Step 1: Write the failing test**

Check that `launcher.css` declares the SFO neon token names and original accent colours, and no longer declares the warm paper/moss variables as the shell identity.
Check that button/control radius tokens exist and that launcher buttons do not use pill-shaped `999px` radii.

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test src-tauri/launcher/aesthetic-baseline.test.mjs`

Expected: FAIL because the current launcher still uses warm paper/moss tokens.

### Task 2: Apply The Neon Baseline

**Files:**
- Modify: `src-tauri/launcher/launcher.css`
- Modify: `src-tauri/launcher/index.html`

- [ ] **Step 1: Replace warm shell tokens with SFO neon tokens**

Use dark navy surfaces, electric pink/blue/cyan accents, restrained glow, and practical sans-serif typography.

- [ ] **Step 2: Update launcher copy**

Describe the shell as the SFO Rust client rather than a generic workflow refinement page.

- [ ] **Step 3: Run checks**

Run:

```bash
node --test src-tauri/launcher/aesthetic-baseline.test.mjs
node --test src-tauri/launcher/*.test.mjs
node --check src-tauri/launcher/launcher.js
node --check src-tauri/launcher/client.js
```

Expected: all checks pass.

### Task 3: Visual Review

**Files:**
- Inspect: `src-tauri/launcher/index.html`
- Inspect: `src-tauri/launcher/launcher.css`

- [ ] **Step 1: Open or build the launcher**

Use the existing Tauri/dev workflow if available, or inspect the static launcher in a local browser.

- [ ] **Step 2: Review against the baseline**

Confirm that the shell now reads as SFO neon, feels calmer than the old Python UI, and remains usable on mobile widths.
