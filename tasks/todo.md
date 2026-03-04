# TeleClaude — TODO

## Current Score: ~28 features | Leader: RichardAtCT at ~35

---

## Phase 1 — High Impact, Low Effort

### [ ] Cancel running request
- `/cancel` to abort a long-running Claude process (kill subprocess, notify user)
- **4 competitors have it**: claudegram, linuz90, hanxiao, chatcode
- Effort: low — kill `proc`, clear state, send confirmation

### [ ] Session list/pick
- `/sessions` to list past sessions, `/session <id>` to resume any
- **3 competitors have it**: claudegram, linuz90, hanxiao
- Effort: medium — extend SQLite to store multiple sessions per user, add list/switch commands

### [ ] Inline keyboard buttons
- Quick-action buttons below responses (New Session, Switch Model, Cancel, etc.)
- **5 competitors have it**: RichardAtCT, claudegram, linuz90, chatcode, Claude-Code-Remote
- Effort: medium — `InlineKeyboardMarkup` on key messages, callback query handler

---

## Phase 2 — Safety & Multi-User

### [ ] Rate limiting
- Throttle requests per user (e.g. max N requests per minute)
- **2 competitors have it**: RichardAtCT, (implied by others)
- Effort: low — simple per-user counter with time window

### [ ] Spending limits
- Max cost per user per day/session, warn and block when exceeded
- **1 competitor has it**: RichardAtCT (but critical for safety if sharing bot)
- Effort: low-medium — check `total_cost` before each run, configurable limit in env

### [ ] Audit logging
- Log security events: auth attempts, commands run, file access, errors
- **2 competitors have it**: RichardAtCT, linuz90
- Effort: low — structured logging to file, rotate daily

---

## Phase 3 — Power Features

### [ ] Git integration
- `/git status`, `/git log`, `/clone <url>` — basic git ops from chat
- **2 competitors have it**: RichardAtCT, chatcode
- Effort: medium — subprocess calls, output formatting

### [ ] Directory browser
- Inline keyboard file navigation (tap folders to browse, tap files to view)
- **2 competitors have it**: RichardAtCT, chatcode
- Effort: medium-high — recursive inline keyboard callbacks, path state management

### [ ] Archive extraction
- Handle ZIP/TAR uploads — extract and pass contents to Claude
- **2 competitors have it**: RichardAtCT, linuz90
- Effort: low-medium — `zipfile`/`tarfile` stdlib, extract to temp dir

---

## Phase 4 — Nice to Have

### [ ] TTS (text-to-speech)
- Speak Claude's responses back as voice messages
- **1 competitor has it**: claudegram (13 voices)
- Effort: medium — needs TTS API (e.g. OpenAI TTS, ElevenLabs)

### [ ] Extended thinking mode
- Trigger deep reasoning mode for complex problems
- **1 competitor has it**: linuz90
- Effort: low — pass `--thinking` flag or model param

### [ ] GitHub webhooks
- Auto-notify on push/PR events to a watched repo
- **2 competitors have it**: RichardAtCT, nclaw
- Effort: medium-high — webhook receiver endpoint, event formatting

### [ ] Telegraph Instant View
- Long responses rendered as Telegraph instant-view pages (clean reading)
- **1 competitor has it**: claudegram
- Effort: medium — Telegraph API integration, HTML conversion

### [ ] Forum topic isolation
- Each conversation in a separate Telegram forum topic
- **2 competitors have it**: claudegram, nclaw
- Effort: medium — topic creation, message routing by topic ID

### [ ] Token usage display
- Show input/output token counts per message
- **1 competitor has it**: claudegram
- Effort: low — parse from stream-json output, add to footer

---

## Completed

- [x] Text → Claude
- [x] Photo/image analysis
- [x] Document upload (PDF, etc.)
- [x] Voice transcription (Groq Whisper)
- [x] Streaming responses (multi-turn tool use)
- [x] Persistent typing indicator
- [x] Tool use visibility
- [x] Session persistence (SQLite)
- [x] Session resume
- [x] Set working directory
- [x] List projects
- [x] File download from server
- [x] Model switching
- [x] Permission mode toggle
- [x] Cost tracking + per-message footer
- [x] Cron scheduling + job persistence
- [x] User whitelist
- [x] Path sandboxing
- [x] Skill auto-discovery
- [x] Markdown → HTML conversion
- [x] Smart message chunking
- [x] Long response as file
- [x] macOS LaunchAgent
- [x] SOCKS5 proxy support
