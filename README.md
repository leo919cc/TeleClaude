# TeleClaude

**Tele**gram + **Claude** — control [Claude Code](https://claude.com/claude-code) remotely from any device via Telegram.

```
Phone/Laptop → Telegram → Bot API → TeleClaude (your machine) → claude -p → response → Telegram
```

## Features

### Core
- **Full Claude Code access** — send any prompt, get Claude's response
- **Voice messages** — send voice/audio, transcribed via Groq Whisper and forwarded to Claude
- **Image & document support** — photos, PDFs, text files — Claude analyzes them
- **Rich formatting** — Markdown → Telegram HTML (headers, code blocks, blockquotes)
- **Smart chunking** — long responses split at 4096-char limit, respects formatting
- **Auto file attachments** — long responses auto-sent as `.md`; files Claude creates are sent to chat

### Streaming & Visibility
- **Tool use visibility** — see what Claude is doing in real time: `Reading config.py`, `$ npm test`, `Editing bot.py`
- **Persistent typing indicator** — "typing..." refreshes every 5s until response arrives
- **Per-message cost footer** — every response shows `[$0.0123 · 4.5s]`

### Session Management
- **Session persistence** — SQLite-backed, survives bot restarts (project, model, cost, session ID)
- **Session resume** — conversations continue via `--resume` until you `/new`
- **Project awareness** — set a working directory so Claude sees your codebase

### Scheduling
- **Cron scheduling** — `/schedule */5 * * * * check server status` for recurring prompts
- **Job persistence** — scheduled jobs survive restarts

### Models & Permissions
- **Model switching** — `/model opus` to change models on the fly
- **Permission toggle** — switch between full access and safe mode

### Skills & Extensibility
- **Skill auto-discovery** — all Claude Code skills (`/commit`, `/review`, etc.) available as Telegram commands
- **File download** — `/getfile <path>` to grab any file from your machine

### Security
- **User whitelist** — only responds to authorized Telegram user IDs
- **Path sandboxing** — file operations restricted to configured base directory

### Infrastructure
- **macOS LaunchAgent** — auto-start on boot, restart on crash
- **SOCKS5 proxy support** — for restricted network environments
- **Configurable timeout** — per-request time limit

## Prerequisites

- **Python 3.10+**
- **[Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code/overview)** installed and authenticated
- **Telegram account**

## Setup

### 1. Create a Telegram bot

1. Open [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot`, follow the prompts
3. Save your **bot token** (looks like `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

### 2. Get your Telegram user ID

1. Open [@userinfobot](https://t.me/userinfobot) on Telegram
2. Send any message — it replies with your **user ID**

### 3. Clone and configure

```bash
git clone https://github.com/leo919cc/TeleClaude.git
cd TeleClaude
cp .env.example .env
```

Edit `.env`:

```
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_USER_ID=123456789
GROQ_API_KEY=your_groq_api_key    # optional, for voice transcription
```

Multiple users: `TELEGRAM_USER_ID=111,222,333`

### 4. Install and run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 bot.py
```

### 5. (Optional) Auto-start on macOS

```bash
./install.sh
```

Creates a LaunchAgent that starts on login and restarts on crash.

```bash
# Stop
launchctl unload ~/Library/LaunchAgents/com.$(whoami).claude-tg-bridge.plist

# Start
launchctl load ~/Library/LaunchAgents/com.$(whoami).claude-tg-bridge.plist
```

## Commands

### Session

| Command | Description |
|---------|-------------|
| `/project <path>` | Set working directory (relative to ~/Documents or absolute) |
| `/projects` | List available projects |
| `/new` | Clear session, start fresh |
| `/status` | Show current project and session info |

### Tools

| Command | Description |
|---------|-------------|
| `/cost` | Session cost, duration, message count |
| `/model <name>` | Switch model (`opus`, `sonnet`, `haiku`, or full ID) |
| `/permissions` | Toggle between full access and safe mode |
| `/config` | View Claude Code settings |
| `/getfile <path>` | Download a file from your machine |
| `/skills` | List available skills |

### Scheduling

| Command | Description |
|---------|-------------|
| `/schedule <cron> <prompt>` | Schedule recurring Claude runs (5-field cron) |
| `/jobs` | List scheduled jobs |
| `/canceljob <id>` | Remove a scheduled job |

### Media

Send **photos**, **documents** (PDF, txt, json, csv), or **voice messages** directly — Claude will process them. Add a caption for specific instructions.

### Skills

Claude Code skills are auto-discovered and registered as Telegram commands:

| Command | Description |
|---------|-------------|
| `/commit` | Create a git commit |
| `/review` | Self-review recent changes |
| `/sync` | Pull latest, read task state |
| `/wrap` | Commit, push, update tracking |

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | Yes | — | Bot token from @BotFather |
| `TELEGRAM_USER_ID` | Yes | — | Comma-separated allowed user IDs |
| `GROQ_API_KEY` | No | — | Groq API key for voice transcription |
| `CLAUDE_PATH` | No | `/opt/homebrew/bin/claude` | Path to Claude CLI |
| `CLAUDE_TIMEOUT` | No | `300` | Max seconds per request |
| `ALLOWED_BASE` | No | `~/Documents` | Base directory for project paths |

## Architecture

```
bot.py              — Telegram handlers, streaming, typing indicator
claude_runner.py    — Async subprocess wrapper for claude -p (JSON + stream-json)
db.py               — SQLite session persistence
scheduler.py        — APScheduler cron job system with JSON persistence
skills.py           — Auto-discovers skills from ~/.claude/
config.py           — Env loading, validation
utils.py            — Message splitting, Markdown→HTML, file detection
```

## License

MIT
