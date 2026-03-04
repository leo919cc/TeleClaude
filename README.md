# claude-tg-bridge

Telegram bot that bridges messages to [Claude Code](https://claude.com/claude-code) CLI, letting you control Claude Code remotely from any device via Telegram.

```
Phone/Laptop → Telegram → Bot API → bot.py (your machine) → claude -p → response → Telegram
```

## Setup

1. Create a bot via [@BotFather](https://t.me/BotFather) and get the token
2. Get your Telegram user ID (message [@userinfobot](https://t.me/userinfobot))
3. Install [Claude Code](https://claude.com/claude-code) CLI

```bash
git clone https://github.com/claw919/claude-tg-bridge.git
cd claude-tg-bridge
cp .env.example .env
# Edit .env with your bot token and user ID
```

### Run manually

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python3 bot.py
```

### Run as macOS LaunchAgent (auto-start on boot)

```bash
./install.sh
```

## Commands

| Command | Description |
|---------|-------------|
| `/project <path>` | Set working directory (relative to ~/Documents or absolute) |
| `/projects` | List available projects |
| `/new` | Clear session, start fresh |
| `/status` | Show current project and session info |
| `/help` | Show available commands |

Any non-command message is sent directly to Claude.

## Features

- **Session continuity** — conversations persist via `--resume` until you `/new`
- **Project awareness** — set a working directory so Claude sees your codebase
- **User whitelist** — only responds to authorized Telegram user IDs
- **Auto-split** — long responses are split to fit Telegram's 4096 char limit
- **Cost tracking** — each response shows cost and duration in the footer
- **Auto-restart** — LaunchAgent restarts the bot on crash or reboot

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | Yes | — | Bot token from @BotFather |
| `TELEGRAM_USER_ID` | Yes | — | Comma-separated allowed user IDs |
| `CLAUDE_PATH` | No | `/opt/homebrew/bin/claude` | Path to claude CLI |
| `CLAUDE_TIMEOUT` | No | `300` | Max seconds per request |
| `ALLOWED_BASE` | No | `~/Documents` | Base directory for project paths |

## License

MIT
