# Mobile Secure Storage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Store the Rust API token outside browser local storage when the Tauri app runs on macOS/iOS.

**Architecture:** Keep `serverUrl` in local storage because it is not secret. Move `apiToken` through an async credential boundary in the launcher; when Tauri's global API is available, the boundary calls Rust commands that read/write Apple Keychain, otherwise browser-only tests/dev fall back to local storage.

**Tech Stack:** Tauri v2 commands, Apple Security.framework via the Rust `security-framework` crate, static ES modules, Node test runner.

---

### Task 1: Launcher Credential Boundary

**Files:**
- Modify: `src-tauri/launcher/client.js`
- Modify: `src-tauri/launcher/client.test.mjs`
- Modify: `src-tauri/launcher/launcher.js`

- [ ] **Step 1: Write failing launcher tests**

Add tests that expect `loadSettings` and `saveSettings` to call a supplied Tauri `invoke` function for `get_api_token`, `set_api_token`, and `clear_api_token`, migrate a legacy local-storage token into native storage, and report native storage copy in connection guidance.

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test src-tauri/launcher/client.test.mjs`

Expected: FAIL because settings helpers are still synchronous and only use local storage.

- [ ] **Step 3: Implement minimal launcher changes**

Make settings helpers async, add `getTauriInvoke`, migrate legacy local-storage tokens to native storage when available, remove local token writes when native storage is available, and update `launcher.js` submit/reset/startup flows to await settings persistence.

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test src-tauri/launcher/client.test.mjs`

Expected: PASS.

### Task 2: Tauri Keychain Commands

**Files:**
- Modify: `src-tauri/Cargo.toml`
- Modify: `src-tauri/tauri.conf.json`
- Modify: `src-tauri/src/lib.rs`
- Create: `src-tauri/src/credential_store.rs`
- Modify: `src-tauri/launcher/mobile-scaffold.test.mjs`

- [ ] **Step 1: Write failing Rust/config tests**

Add source-level tests that require `app.withGlobalTauri: true`, `invoke_handler(tauri::generate_handler![get_api_token, set_api_token, clear_api_token])`, and `security-framework` in `Cargo.toml`.

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test src-tauri/launcher/mobile-scaffold.test.mjs`

Expected: FAIL because commands and global Tauri are not configured yet.

- [ ] **Step 3: Implement minimal Rust command bridge**

Add the `security-framework` dependency, implement Apple Keychain get/set/delete helpers for macOS/iOS, provide clear unsupported-platform errors elsewhere, register Tauri commands, and enable `app.withGlobalTauri`.

- [ ] **Step 4: Run tests to verify it passes**

Run: `node --test src-tauri/launcher/mobile-scaffold.test.mjs`

Expected: PASS.

### Task 3: Docs And Verification

**Files:**
- Modify: `docs/rust_mobile_connection_shell.md`
- Modify: `docs/rust_rewrite_parity_review.md`

- [ ] **Step 1: Update docs**

Record that API tokens now use Apple Keychain on macOS/iOS through Tauri commands, and that browser-only fallback remains local storage for non-Tauri development.

- [ ] **Step 2: Run focused verification**

Run:
- `node --test src-tauri/launcher/*.test.mjs`
- `node --check src-tauri/launcher/launcher.js`
- `PATH="$HOME/.cargo/bin:$PATH" cargo fmt --all --check`
- `PATH="$HOME/.cargo/bin:$PATH" cargo test`
- `scripts/build_tauri_ios_simulator.sh`
- `git diff --check`

Expected: all commands exit 0.

- [ ] **Step 3: Commit and push**

Commit message: `feat: store api token in apple keychain`
