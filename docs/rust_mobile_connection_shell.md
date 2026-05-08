# SFO Mobile Connection Shell

Date: 2026-05-08

This note tracks the first connection slice for the future iPhone client. The goal is to make the server relationship explicit before building more mobile screens.

## Implemented In The Shared Shell

- The connection card now classifies the configured server as `Simulator / this Mac`, `LAN / VPN`, or `Remote / routed`.
- Loopback addresses such as `127.0.0.1` are called out as simulator/Mac-only: the iOS Simulator on the Mac can reach the Mac process, but a physical iPhone cannot reach it through its own loopback address.
- Private HTTP is described as acceptable only on a trusted LAN or VPN during prototype use.
- HTTPS is called out as the right default for anything reachable outside a trusted LAN.
- Auth status starts as unknown, then updates after `/api/v1/auth/status` reports whether bearer-token auth is required.
- The shell states that desktop token storage is temporary local storage and that the iPhone build must use platform-secure storage before real use.

## Current Local iOS Readiness

Checked on 2026-05-08 in the Rust rewrite worktree.

Available:

- `cargo tauri ios` is available through `tauri-cli 2.9.6`.
- The CLI exposes `init`, `dev`, `build`, and `run` commands for iOS.
- Full Xcode is selected at `/Applications/Xcode.app/Contents/Developer`.
- CocoaPods is installed.
- Rust iOS targets are installed for device and simulator builds.
- The Tauri iOS scaffold has been generated under `src-tauri/gen/apple`.
- `scripts/build_tauri_ios_simulator.sh` builds a simulator bundle at `src-tauri/gen/apple/build/arm64-sim/Start Finishing Organiser.app`.
- The wrapper clears the two ignored generated `.app` outputs first because repeat `cargo tauri ios build --debug --target aarch64-sim --ci` runs can fail when Tauri renames over a non-empty generated bundle directory.
- The simulator bundle installs and launches on the iPhone 17 Pro simulator against the local Rust server at `http://127.0.0.1:8088`.
- The simulator smoke run verified connection status, `/api/v1/bootstrap`, quick capture into the inbox, and the phone-reach copy.
- The generated Xcode prebuild script pins `CARGO` and `RUSTC` to rustup's `$HOME/.cargo/bin` tools, because Homebrew Rust is earlier on this machine's default `PATH` and does not have the iOS std targets.

Still blocked locally:

- Physical-device and release/archive signing need an Apple Development certificate and development team ID through `bundle > iOS > developmentTeam` or the `APPLE_DEVELOPMENT_TEAM` environment variable.

Tauri's mobile prerequisites and CLI reference remain the authoritative references for setup:

- [Tauri prerequisites](https://v2.tauri.app/start/prerequisites/)
- [Tauri CLI reference](https://v2.tauri.app/reference/cli/)

## Remaining Mobile Connection Work

- Add platform-secure credential storage for the API token before real use.
- Decide whether Mac mini access is LAN-only, VPN-only, or exposed through an HTTPS reverse proxy.
- Add a phone-shaped Settings screen around the same connection guidance rather than copying the full Mac dashboard.
- Verify connection against a Mac mini server URL from a physical iPhone on the intended LAN/VPN path.
