# Competitive Analysis — Claude Telegram Bots

Last updated: 2026-03-04

**Legend:** Y = we have it, ~ = partial, — = we don't have it

## Competitors

| # | Project | Stars | Language | Notes |
|---|---------|-------|----------|-------|
| 1 | [RichardAtCT/claude-code-telegram](https://github.com/RichardAtCT/claude-code-telegram) | ~1,900 | Python | Most enterprise-grade |
| 2 | [NachoSEO/claudegram](https://github.com/NachoSEO/claudegram) | ~81 | TypeScript | Richest media features |
| 3 | [linuz90/claude-telegram-bot](https://github.com/linuz90/claude-telegram-bot) | ~389 | TypeScript | Polished personal assistant |
| 4 | [godagoo/claude-telegram-relay](https://github.com/godagoo/claude-telegram-relay) | ~302 | TypeScript | Memory + proactive check-ins |
| 5 | [hanxiao/claudecode-telegram](https://github.com/hanxiao/claudecode-telegram) | ~507 | Python | tmux-based, Cloudflare tunnel |
| 6 | [Nickqiaoo/chatcode](https://github.com/Nickqiaoo/chatcode) | ~69 | TypeScript | Visual diffs, inline permissions |
| 7 | [JessyTsui/Claude-Code-Remote](https://github.com/JessyTsui/Claude-Code-Remote) | ~1,100 | JavaScript | Multi-platform (Email, LINE, Telegram) |
| 8 | [nickalie/nclaw](https://github.com/nickalie/nclaw) | ~4 | Go | 580+ models, Docker/K8s native |

---

## Feature Matrix

### Core Messaging

| Feature | Ours | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---------|------|---|---|---|---|---|---|---|---|
| Text → Claude | Y | Y | Y | Y | Y | Y | Y | Y | Y |
| Photo/image analysis | Y | Y | Y | Y | Y | — | Y | — | Y |
| Document upload (PDF, etc.) | Y | Y | Y | Y | — | — | — | — | Y |
| Archive extraction (ZIP/TAR) | — | Y | — | Y | — | — | — | — | — |
| Video message processing | — | — | — | Y | — | — | — | — | — |

### Voice & Audio

| Feature | Ours | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---------|------|---|---|---|---|---|---|---|---|
| Voice transcription | Y | Y | Y | Y | Y | — | Y | — | Y |
| Standalone transcribe command | — | — | Y | — | — | — | — | — | — |
| Text-to-speech (TTS) | — | — | Y | — | — | — | — | — | — |
| Multiple TTS voices | — | — | Y (13) | — | — | — | — | — | — |
| Local Whisper fallback | — | — | — | — | Y | — | — | — | — |

### Streaming & Visibility

| Feature | Ours | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---------|------|---|---|---|---|---|---|---|---|
| Streaming responses | ~ | Y | Y | Y | — | — | Y | — | Y |
| Persistent typing indicator | Y | Y | — | — | — | — | — | — | — |
| Tool use visibility | Y | Y | Y | — | — | — | — | — | — |
| Verbose levels (0-2) | — | Y | — | — | — | — | — | — | — |
| Terminal-style UI toggle | — | — | Y | — | — | — | — | — | — |

### Session Management

| Feature | Ours | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---------|------|---|---|---|---|---|---|---|---|
| Session persistence | Y | Y | Y | Y | Y | Y | Y | Y | Y |
| Session resume | Y | Y | Y | Y | Y | Y | Y | — | Y |
| Session export (MD/HTML/JSON) | — | Y | — | — | — | — | — | — | — |
| Multiple session list/pick | — | — | Y | Y | — | Y | — | — | — |
| Forum topic isolation | — | — | Y | — | — | — | — | — | Y |
| Configurable session timeout | — | — | — | — | — | — | Y | — | — |

### Project & File Management

| Feature | Ours | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---------|------|---|---|---|---|---|---|---|---|
| Set working directory | Y | Y | Y | — | — | — | Y | — | — |
| List projects | Y | Y | Y | — | — | — | Y | — | — |
| File download from server | Y | Y | Y | — | — | — | Y | — | — |
| Directory browser (inline KB) | — | Y | — | — | — | — | Y | — | — |
| Visual diff display | — | — | — | — | — | — | Y | — | — |
| Git integration (clone, status) | — | Y | — | — | — | — | Y | — | — |
| GitHub CLI (gh) integration | — | Y | — | — | — | — | — | — | — |
| Clone repos via bot | — | — | — | — | — | — | Y | — | — |

### Models & Permissions

| Feature | Ours | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---------|------|---|---|---|---|---|---|---|---|
| Model switching | Y | — | Y | — | — | — | Y | — | Y |
| Permission mode toggle | Y | — | — | — | — | — | Y | — | — |
| Inline permission prompts | — | — | — | — | — | — | Y | — | — |
| Multi-model backend (580+) | — | — | — | — | — | — | — | — | Y |
| Extended thinking mode | — | — | — | Y | — | — | — | — | — |
| Plan/explore modes | — | — | Y | — | — | — | Y | — | — |

### Cost & Limits

| Feature | Ours | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---------|------|---|---|---|---|---|---|---|---|
| Cost tracking | Y | Y | — | — | — | — | — | — | — |
| Per-message cost footer | Y | — | — | — | — | — | — | — | — |
| Spending limits per user | — | Y | — | — | — | — | — | — | — |
| Rate limiting | — | Y | — | — | — | — | — | — | — |
| Token usage display | — | — | Y | — | — | — | — | — | — |

### Scheduling & Automation

| Feature | Ours | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---------|------|---|---|---|---|---|---|---|---|
| Cron scheduling | Y | Y | — | — | — | — | — | — | Y |
| Job persistence | Y | Y | — | — | — | — | — | — | — |
| GitHub webhooks | — | Y | — | — | — | — | — | — | Y |
| Proactive check-ins | — | — | — | — | Y | — | — | — | — |
| Morning briefings | — | — | — | — | Y | — | — | — | — |
| Semantic memory search | — | — | — | — | Y | — | — | — | — |

### Security & Auth

| Feature | Ours | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---------|------|---|---|---|---|---|---|---|---|
| User whitelist | Y | Y | Y | Y | Y | — | Y | Y | Y |
| Path sandboxing | Y | Y | Y | Y | — | — | — | — | Y |
| Token-based auth | — | Y | — | — | — | — | Y | Y | — |
| Audit logging | — | Y | — | Y | — | — | — | — | — |
| Input validation/injection protection | — | Y | — | Y | — | — | — | — | — |
| Webhook HMAC verification | — | Y | — | — | — | — | — | — | — |

### Skills & Extensibility

| Feature | Ours | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---------|------|---|---|---|---|---|---|---|---|
| Skill auto-discovery | Y | — | — | — | — | — | — | — | Y |
| Tool allowlist/disallowlist | — | Y | — | — | — | — | — | — | — |
| MCP server integration | — | — | Y | Y | — | — | — | — | — |
| Quick action buttons | — | Y | Y | — | — | — | — | — | — |
| Plugin system | — | Y (planned) | — | — | — | — | — | — | — |

### Content & Media Integrations

| Feature | Ours | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---------|------|---|---|---|---|---|---|---|---|
| Reddit integration | — | — | Y | — | — | — | — | — | — |
| Medium article fetching | — | — | Y | — | — | — | — | — | — |
| YouTube/TikTok extraction | — | — | Y | — | — | — | — | — | — |
| Reddit video download | — | — | Y | — | — | — | — | — | — |
| Telegraph Instant View | — | — | Y | — | — | — | — | — | — |

### Formatting & UX

| Feature | Ours | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---------|------|---|---|---|---|---|---|---|---|
| Markdown → HTML conversion | Y | Y | Y | — | — | — | — | — | Y |
| Smart message chunking | Y | — | Y | — | — | — | Y | — | — |
| Long response as file | Y | — | — | — | — | — | — | — | — |
| Inline keyboard buttons | — | Y | Y | Y | — | — | Y | Y | — |
| Message queue (! prefix) | — | — | — | Y | — | — | — | — | — |
| Cancel running request | — | — | Y | Y | — | Y | Y | — | — |

### Infrastructure & Deployment

| Feature | Ours | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---------|------|---|---|---|---|---|---|---|---|
| macOS LaunchAgent | Y | — | — | Y | — | — | — | — | — |
| Proxy support (SOCKS5) | Y | — | — | — | — | — | — | — | — |
| Docker deployment | — | — | — | — | — | — | — | — | Y |
| Kubernetes / Helm | — | — | — | — | — | — | — | — | Y |
| Cloudflare Tunnel | — | — | — | — | — | Y | — | — | — |
| Multi-platform (Email, LINE) | — | — | — | — | — | — | — | Y | — |
| Cross-platform (Win/Mac/Linux) | — | — | — | — | Y | — | — | — | Y |
| CI/CD pipeline | — | Y | — | — | — | — | — | — | — |

---

## Score Summary

| Project | Total features (from matrix) |
|---------|-----|
| **Ours (claude-tg-bridge)** | ~28 |
| RichardAtCT/claude-code-telegram | ~35 |
| NachoSEO/claudegram | ~30 |
| linuz90/claude-telegram-bot | ~18 |
| godagoo/claude-telegram-relay | ~12 |
| hanxiao/claudecode-telegram | ~6 |
| Nickqiaoo/chatcode | ~20 |
| JessyTsui/Claude-Code-Remote | ~10 |
| nickalie/nclaw | ~18 |

## High-Impact Gaps (worth closing)

Features multiple competitors have that we lack:

1. **Cancel running request** — `/cancel` to abort a long-running Claude process (4 competitors have it)
2. **Inline keyboard buttons** — quick actions, settings toggles (5 competitors)
3. **Rate limiting** — protect against runaway costs (2 competitors)
4. **Spending limits** — max cost per user/session (1 competitor, but critical for safety)
5. **Session list/pick** — resume from multiple past sessions (3 competitors)
6. **Audit logging** — security event log (2 competitors)
7. **Git integration** — clone, status, basic git ops from chat (2 competitors)

## Nice-to-Have Gaps

1. **TTS** — speak responses back (only claudegram)
2. **Extended thinking** — trigger deep reasoning mode (only linuz90)
3. **GitHub webhooks** — auto-notify on push/PR (2 competitors)
4. **Telegraph Instant View** — long responses as instant-view pages (only claudegram)
5. **Directory browser** — inline keyboard file navigation (2 competitors)
6. **Archive extraction** — handle ZIP/TAR uploads (2 competitors)
