# claude-tg-bridge — Feature Reference

## Core

| Feature | Command / Trigger | Description |
|---------|------------------|-------------|
| Text messaging | Any text | Sends prompt to Claude Code CLI, returns formatted response |
| Photo analysis | Send photo | Downloads image, asks Claude to analyze via Read tool |
| Document handling | Send file | Supports PDF, TXT, JSON, CSV, images — Claude reads and responds |
| Voice transcription | Send voice/audio | Transcribes via Groq Whisper API, sends text to Claude |
| Markdown → HTML | Automatic | Converts Claude's markdown to Telegram-compatible HTML |
| Message chunking | Automatic | Splits long responses at 4096-char Telegram limit, respects newlines/spaces |
| Document auto-attach | Automatic | Responses >1500 chars with 2+ headers auto-sent as `.md` file |
| File auto-detection | Automatic | Files created/modified during a run are auto-sent to chat |

## Session Management

| Feature | Command | Description |
|---------|---------|-------------|
| Set project | `/project <path>` | Set working directory (absolute or relative to ~/Documents) |
| List projects | `/projects` | List all directories under ~/Documents |
| Clear session | `/new` | Reset session (clears session_id, keeps project) |
| Session status | `/status` | Show current project and session state |
| Session persistence | Automatic (SQLite) | Sessions survive bot restarts — project, model, cost, session_id all persisted |
| Session resume | Automatic | Uses `--resume` flag to continue Claude conversations across messages |

## Models & Permissions

| Feature | Command | Description |
|---------|---------|-------------|
| Switch model | `/model <name>` | Switch to any Claude model (opus, sonnet, haiku, or full model ID) |
| Permission toggle | `/permissions` | Toggle between `bypassPermissions` (full) and `acceptEdits` (safe) |
| View config | `/config` | Show contents of `~/.claude/settings.json` |

## Cost & Usage

| Feature | Command | Description |
|---------|---------|-------------|
| Cost tracking | `/cost` | Show session cost (USD), total time, message count |
| Per-message footer | Automatic | Each response shows `[$0.0123 · 4.5s]` footer |

## Scheduling

| Feature | Command | Description |
|---------|---------|-------------|
| Schedule prompt | `/schedule <cron> <prompt>` | Cron-based recurring Claude runs (5-field cron expression) |
| List jobs | `/jobs` | Show all scheduled jobs for current user |
| Cancel job | `/canceljob <id>` | Remove a scheduled job |
| Job persistence | Automatic (JSON) | Jobs survive restarts, re-registered with APScheduler on boot |

## Streaming & Visibility

| Feature | Trigger | Description |
|---------|---------|-------------|
| Stream-JSON output | Automatic (text/voice) | Uses `--output-format stream-json --verbose` for multi-turn progress |
| Tool use visibility | Automatic | Shows what Claude is doing: `Reading config.py`, `$ npm test`, `Editing bot.py` |
| Persistent typing | Automatic | "typing..." indicator refreshes every 5s until response arrives |

## Skills

| Feature | Command | Description |
|---------|---------|-------------|
| Auto-discovery | Startup | Discovers skills from `~/.claude/skills/`, `~/.claude/commands/`, plugins |
| Run skill | `/<skill> [args]` | Execute any discovered skill |
| List skills | `/skills` | Show all available skills with descriptions |

## Media & Files

| Feature | Command | Description |
|---------|---------|-------------|
| Download file | `/getfile <path>` | Download any file from the server (under ~/Documents) |
| Photo upload | Send photo | Saved to temp dir, passed to Claude for analysis |
| Document upload | Send file | Saved to temp dir with correct extension, passed to Claude |
| Voice upload | Send voice/audio | Transcribed via Groq Whisper, result sent to Claude |

## Security & Auth

| Feature | Description |
|---------|-------------|
| User whitelist | Comma-separated Telegram user IDs in `TELEGRAM_USER_ID` env var |
| Path sandboxing | All file operations restricted to `ALLOWED_BASE` (default ~/Documents) |
| No secret commits | API keys centralized in `~/Documents/api-keys/.env`, never committed |

## Infrastructure

| Feature | Description |
|---------|-------------|
| LaunchAgent | macOS auto-start via `install.sh` |
| Proxy support | SOCKS5 proxy for Telegram API (auto-detected from `all_proxy` env) |
| Configurable timeout | `CLAUDE_TIMEOUT` env var (default 300s) |
| Graceful error handling | Timeout kills, stderr capture, HTML fallback on formatting errors |
