# Rust Mac Mini Deployment Runbook

This runbook is for the first private-network Rust server deployment. It is not an internet-exposed deployment plan.

## Environment

Use these settings on the Mac mini:

```bash
export SFO_RUST_BIND="0.0.0.0:8088"
export SFO_RUST_DATABASE_URL="sqlite:///Users/rcd58/Library/Application Support/SFO/sfo-rust.db"
export SFO_RUST_API_TOKEN="<long random token>"
```

Generate a token:

```bash
openssl rand -base64 32
```

API clients should send:

```text
Authorization: Bearer <long random token>
```

`GET /healthz` and `GET /api/v1/auth/status` are public. Other `/api/v1/*` endpoints require the token when `SFO_RUST_API_TOKEN` is set.

## Build

Build the server on the Mac mini:

```bash
cargo build --release -p sfo-server
```

Expected binary:

```text
target/release/sfo-server
```

## Launchd

Create `/Users/rcd58/Library/LaunchAgents/com.sfo.rust-server.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.sfo.rust-server</string>

  <key>ProgramArguments</key>
  <array>
    <string>/Users/rcd58/sfo/target/release/sfo-server</string>
  </array>

  <key>WorkingDirectory</key>
  <string>/Users/rcd58/sfo</string>

  <key>EnvironmentVariables</key>
  <dict>
    <key>SFO_RUST_BIND</key>
    <string>0.0.0.0:8088</string>
    <key>SFO_RUST_DATABASE_URL</key>
    <string>sqlite:///Users/rcd58/Library/Application Support/SFO/sfo-rust.db</string>
    <key>SFO_RUST_API_TOKEN</key>
    <string>replace-with-long-random-token</string>
    <key>RUST_LOG</key>
    <string>sfo_server=info,tower_http=info</string>
  </dict>

  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>

  <key>StandardOutPath</key>
  <string>/Users/rcd58/Library/Logs/sfo-rust-server.out.log</string>
  <key>StandardErrorPath</key>
  <string>/Users/rcd58/Library/Logs/sfo-rust-server.err.log</string>
</dict>
</plist>
```

Load or reload:

```bash
launchctl unload ~/Library/LaunchAgents/com.sfo.rust-server.plist 2>/dev/null || true
launchctl load -w ~/Library/LaunchAgents/com.sfo.rust-server.plist
```

Check:

```bash
launchctl print gui/$(id -u)/com.sfo.rust-server
tail -n 50 ~/Library/Logs/sfo-rust-server.err.log
```

If `/api/v1/auth/status` still reports `{"auth_required":false}` after loading this LaunchAgent, check for an older development server occupying the same port:

```bash
lsof -nP -iTCP:8088 -sTCP:LISTEN
launchctl print gui/$(id -u) | grep -i sfo
```

Disable any stale development agent before restarting the production one:

```bash
launchctl unload ~/Library/LaunchAgents/com.sfo.rust-server.dev.plist 2>/dev/null || true
launchctl disable gui/$(id -u)/com.sfo.rust-server.dev 2>/dev/null || true
launchctl kickstart -k gui/$(id -u)/com.sfo.rust-server
```

The macOS Tauri shell stores the API token in Apple Keychain under service `com.rcd58.sfo` and account `rust-api-token`. To retrieve the token for entering it on the iPhone:

```bash
security find-generic-password -s com.rcd58.sfo -a rust-api-token -w
```

## Smoke Tests

From the Mac mini:

```bash
curl http://127.0.0.1:8088/healthz
curl http://127.0.0.1:8088/api/v1/auth/status
curl -H "Authorization: Bearer $SFO_RUST_API_TOKEN" http://127.0.0.1:8088/api/v1/bootstrap
```

From another device on the LAN:

```bash
curl http://<mac-mini-lan-ip>:8088/healthz
curl -H "Authorization: Bearer <token>" http://<mac-mini-lan-ip>:8088/api/v1/bootstrap
```

The iPhone app should store the server URL and token in local secure storage, then call the same API over the LAN. For remote use, prefer a private VPN or Tailscale-style network; do not expose this port directly to the internet.

## Backup Policy

Use `POST /api/v1/export/backup` with the API token to confirm table counts. Imports already create pre-import SQLite backup files. A production run should also copy the SQLite database and backup directory with Time Machine or another Mac mini backup job.
