# TeleClaude

**Tele**gram + **Claude** — control [Claude Code](https://claude.com/claude-code) remotely from any device via Telegram.

I built TeleClaude because I wanted a dead-simple way to talk to Claude Code from my phone. The existing projects are great and packed with features, but they're also 3x to 18x larger in code. I didn't need an enterprise framework — I needed 7 files that do the job and are easy to hack on. So I built my own instead of forking.

**1,626 lines of Python. 7 files. 4 dependencies.**

```
You (any device) → Telegram → TeleClaude (your machine) → claude -p → response back
```

## How It Works

TeleClaude runs on your machine (Mac, Linux, wherever Claude Code is installed) and listens for Telegram messages. When you send a message, it spawns `claude -p` as a subprocess, streams the output, and sends the response back to your Telegram chat. That's it — no server, no database server, no Docker required.

Your Claude Code session persists between messages. Switch projects, change models, schedule recurring prompts — all from Telegram. Every Claude Code skill you have installed (`/commit`, `/review`, etc.) is auto-discovered and available as a Telegram command.

## Features

### Talk to Claude from Anywhere

Send text, photos, documents (PDF, txt, json, csv), or voice messages. Claude sees everything.

- **Voice transcription** — voice and audio messages are transcribed via [Groq Whisper](https://groq.com/) and forwarded to Claude as text. Free tier, fast, no local model needed
- **Image analysis** — send a photo, Claude reads it via its Read tool
- **Document handling** — PDFs, text files, CSVs — saved to a temp directory and passed to Claude with full context

### See What Claude Is Doing

While Claude works, you see real-time status updates in your chat:

```
Reading config.py
$ npm test
Editing bot.py
Grep: TODO
```

A persistent typing indicator stays active the entire time (refreshes every 5s so Telegram doesn't drop it). When Claude responds, you see a cost and duration footer on every message:

```
[$0.0847 · 12.3s]
```

### Session Management

Sessions are backed by SQLite and survive bot restarts — your project, model, cost history, and Claude session ID are all persisted. Conversations continue seamlessly via `--resume` until you explicitly start fresh with `/new`.

Switch between projects with `/project myapp` and Claude instantly has your full codebase context.

### Cron Scheduling

Schedule recurring Claude prompts with standard cron expressions:

```
/schedule 0 9 * * * summarize overnight git commits
/schedule */30 * * * * check if production is healthy
```

Jobs persist across restarts (JSON file). List with `/jobs`, remove with `/canceljob <id>`.

### Model & Permission Control

- `/model opus` — switch models on the fly (opus, sonnet, haiku, or any full model ID)
- `/permissions` — toggle between `bypassPermissions` (full autonomy) and `acceptEdits` (safe mode, edits only)

### Smart Output

- **Markdown → HTML** — Claude's markdown is converted to Telegram-compatible HTML with proper headers, code blocks, and blockquotes
- **Message chunking** — long responses are split at Telegram's 4096-char limit, respecting formatting boundaries
- **Auto file attachment** — responses over 1500 chars with multiple headers are auto-sent as `.md` files for better readability
- **File detection** — files Claude creates or modifies during a run are automatically sent to your chat

### Skill Mirroring

All Claude Code skills installed on your machine (`~/.claude/skills/`, `~/.claude/commands/`, plugins) are auto-discovered at startup and registered as Telegram commands. If you have `/commit`, `/review`, `/sync` in Claude Code, you have them in Telegram too.

### Security

- **User whitelist** — only Telegram user IDs listed in `TELEGRAM_USER_ID` can interact with the bot
- **Path sandboxing** — all file operations (projects, downloads) are restricted to `ALLOWED_BASE` (default `~/Documents`)

## Why So Small?

| Project | Language | Source Lines | Files |
|---------|----------|-------------|-------|
| **TeleClaude** | **Python** | **1,626** | **7** |
| godagoo/claude-telegram-relay | TypeScript | ~2,200 | 15 |
| linuz90/claude-telegram-bot | TypeScript | ~3,500 | 20 |
| Nickqiaoo/chatcode | TypeScript | ~5,800 | 34 |
| nickalie/nclaw | Go | ~8,600 | 55 |
| NachoSEO/claudegram | TypeScript | ~12,300 | 48 |
| RichardAtCT/claude-code-telegram | Python | ~29,000 | 109 |

TeleClaude is intentionally minimal. The goal is a lightweight personal tool that covers the features that matter most — not an enterprise platform. Every feature earns its lines of code.

4 Python dependencies: `python-telegram-bot`, `python-dotenv`, `apscheduler`, `croniter`.

## Inspiration & Credits

TeleClaude is inspired by features from several excellent projects in this space:

- **[RichardAtCT/claude-code-telegram](https://github.com/RichardAtCT/claude-code-telegram)** — the most feature-complete project out there. Inspired our cost tracking, persistent typing indicator, and tool use visibility
- **[NachoSEO/claudegram](https://github.com/NachoSEO/claudegram)** — richest media features. Inspired our voice transcription and skill mirroring approach
- **[linuz90/claude-telegram-bot](https://github.com/linuz90/claude-telegram-bot)** — polished personal assistant feel. Inspired our session persistence and project switching
- **[godagoo/claude-telegram-relay](https://github.com/godagoo/claude-telegram-relay)** — memory and proactive check-ins. Inspired our scheduling system
- **[Nickqiaoo/chatcode](https://github.com/Nickqiaoo/chatcode)** — visual diffs and inline permissions. On our roadmap
- **[nickalie/nclaw](https://github.com/nickalie/nclaw)** — Docker/K8s native, multi-model support. Inspired our model switching

Thank you to all these projects for pushing the space forward.

## Setup

### 1. Create a Telegram bot

1. Open [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot`, follow the prompts
3. Save your **bot token**

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
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_USER_ID=your-user-id
GROQ_API_KEY=your-groq-key          # optional, for voice transcription
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

## Commands

| Command | Description |
|---------|-------------|
| `/project <path>` | Set working directory |
| `/projects` | List available projects |
| `/new` | Clear session, start fresh |
| `/status` | Current project and session info |
| `/cost` | Session cost, duration, message count |
| `/model <name>` | Switch model (opus, sonnet, haiku) |
| `/permissions` | Toggle full access / safe mode |
| `/config` | View Claude Code settings |
| `/getfile <path>` | Download a file from your machine |
| `/skills` | List available skills |
| `/schedule <cron> <prompt>` | Schedule recurring Claude runs |
| `/jobs` | List scheduled jobs |
| `/canceljob <id>` | Remove a scheduled job |

Send **photos**, **documents**, or **voice messages** directly — no command needed.

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
bot.py           815 lines  — Telegram handlers, streaming, typing indicator
claude_runner.py 265 lines  — Async subprocess wrapper for claude -p
skills.py        175 lines  — Auto-discovers skills from ~/.claude/
utils.py         138 lines  — Message splitting, Markdown→HTML, file detection
scheduler.py     125 lines  — APScheduler cron job system
db.py             73 lines  — SQLite session persistence
config.py         35 lines  — Env loading, validation
```

## License

MIT
