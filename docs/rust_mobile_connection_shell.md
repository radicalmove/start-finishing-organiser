# SFO Mobile Connection Shell

Date: 2026-05-08

This note tracks the first connection slice for the future iPhone client. The goal is to make the server relationship explicit before building more mobile screens.

## Implemented In The Shared Shell

- The connection card now classifies the configured server as `This Mac only`, `LAN / VPN`, or `Remote / routed`.
- Loopback addresses such as `127.0.0.1` are called out as desktop-only because an iPhone cannot reach the Mac process through its own loopback address.
- Private HTTP is described as acceptable only on a trusted LAN or VPN during prototype use.
- HTTPS is called out as the right default for anything reachable outside a trusted LAN.
- Auth status starts as unknown, then updates after `/api/v1/auth/status` reports whether bearer-token auth is required.
- The shell states that desktop token storage is temporary local storage and that the iPhone build must use platform-secure storage before real use.

## Current Local iOS Readiness

Checked on 2026-05-08 in the Rust rewrite worktree.

Available:

- `cargo tauri ios` is available through `tauri-cli 2.9.6`.
- The CLI exposes `init`, `dev`, `build`, and `run` commands for iOS.

Blocked locally:

- `xcodebuild -version` fails because `xcode-select` points at Command Line Tools, not full Xcode.
- `pod` is not installed, so CocoaPods is unavailable.
- `rustup target list --installed` only shows `aarch64-apple-darwin`; iOS device and simulator targets are not installed yet.

Do not run `cargo tauri ios init` as the next automated step until the full Xcode install is selected and CocoaPods/Rust target setup is ready. Tauri's mobile prerequisites and CLI reference are the authoritative references for that setup:

- [Tauri prerequisites](https://v2.tauri.app/start/prerequisites/)
- [Tauri CLI reference](https://v2.tauri.app/reference/cli/)

## Remaining Mobile Connection Work

- Generate the iOS project once the local toolchain is ready.
- Add platform-secure credential storage for the API token before real use.
- Decide whether Mac mini access is LAN-only, VPN-only, or exposed through an HTTPS reverse proxy.
- Add a phone-shaped Settings screen around the same connection guidance rather than copying the full Mac dashboard.
- Verify connection against a Mac mini server URL from an actual iPhone simulator or device.
