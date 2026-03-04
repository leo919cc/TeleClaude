# claude-tg-bridge

Telegram bot that bridges messages to [Claude Code](https://claude.com/claude-code) CLI, letting you control Claude Code remotely from any device via Telegram.

```
Phone/Laptop → Telegram → Bot API → bot.py (your machine) → claude -p → response → Telegram
```

## Features

- **Full Claude Code access** — send any prompt from Telegram, get Claude's response back
- **Session continuity** — conversations persist via `--resume` until you `/new`
- **Project awareness** — set a working directory so Claude sees your codebase
- **Image & document support** — send photos, PDFs, text files — Claude analyzes them via its Read tool
- **Rich formatting** — Markdown responses are converted to Telegram HTML (bold headers, code blocks, blockquotes)
- **Auto file attachments** — long document responses auto-attach as `.md` files; files Claude creates are sent to you
- **File download** — `/getfile <path>` to download any file from your machine
- **Skill mirroring** — all Claude Code skills (`/commit`, `/review`, `/sync`, etc.) auto-discovered and available as Telegram commands
- **Model switching** — `/model opus` to change models on the fly
- **Cost tracking** — per-message cost/duration in footer, `/cost` for session totals
- **User whitelist** — only responds to authorized Telegram user IDs
- **Auto-restart** — LaunchAgent restarts the bot on crash or reboot (macOS)

## Prerequisites

- **Python 3.10+**
- **[Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code/overview)** installed and authenticated (`claude` command must work in your terminal)
- **Telegram account**

## Setup

### 1. Create a Telegram bot

1. Open Telegram and search for [@BotFather](https://t.me/BotFather)
2. Send `/newbot` and follow the prompts to choose a name and username
3. BotFather will reply with your **bot token** — save it (looks like `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

### 2. Get your Telegram user ID

1. Search for [@userinfobot](https://t.me/userinfobot) on Telegram
2. Send it any message — it will reply with your **user ID** (a number like `123456789`)
3. This is used to restrict the bot to only respond to you

### 3. Clone and configure

```bash
git clone https://github.com/leo919pm/claude-tg-bridge.git
cd claude-tg-bridge
cp .env.example .env
```

Edit `.env` with your values:

```
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_USER_ID=123456789
```

To allow multiple users, separate IDs with commas: `TELEGRAM_USER_ID=111,222,333`

### 4. Install and run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 bot.py
```

Open your bot in Telegram and send a message — you should get a response from Claude.

### 5. (Optional) Auto-start on macOS

To run the bot automatically on boot and restart on crash:

```bash
./install.sh
```

This creates a macOS LaunchAgent and a service copy outside `~/Documents/` (to avoid macOS privacy restrictions). The bot will start on login and show a dialog if it crashes.

To stop: `launchctl unload ~/Library/LaunchAgents/com.$(whoami).claude-tg-bridge.plist`

To start again: `launchctl load ~/Library/LaunchAgents/com.$(whoami).claude-tg-bridge.plist`

Or double-click `start.command` to run manually from Finder.

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
| `/cost` | Show session cost, duration, and message count |
| `/model <name>` | Switch AI model (e.g. `opus`, `sonnet`, `haiku`, `default`) |
| `/config` | View Claude Code settings (read-only) |
| `/getfile <path>` | Download a file from your machine |
| `/skills` | List all available skills |

### Media

Send a **photo** or **document** (PDF, txt, json, csv) directly in the chat — Claude will read and analyze it. Add a caption for specific instructions.

### Skills

All Claude Code skills are auto-discovered from `~/.claude/` and registered as Telegram commands. Examples:

| Command | Description |
|---------|-------------|
| `/commit` | Create a git commit |
| `/review` | Self-review recent code changes |
| `/sync` | Pull latest changes, read task state |
| `/wrap` | Commit, push, and update task tracking |

Any non-command message is sent directly to Claude as a prompt.

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | Yes | — | Bot token from @BotFather |
| `TELEGRAM_USER_ID` | Yes | — | Comma-separated allowed user IDs |
| `CLAUDE_PATH` | No | `/opt/homebrew/bin/claude` | Path to Claude CLI |
| `CLAUDE_TIMEOUT` | No | `300` | Max seconds per request |
| `ALLOWED_BASE` | No | `~/Documents` | Base directory for project paths |

## Architecture

```
bot.py              — Telegram handlers, entry point
claude_runner.py    — Async subprocess wrapper for claude -p
skills.py           — Auto-discovers skills from ~/.claude/
config.py           — Env loading, validation
utils.py            — Message splitting, Markdown→HTML, file detection
```

## License

MIT
