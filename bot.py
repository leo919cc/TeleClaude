"""Telegram → Claude Code bridge bot."""

import asyncio
import html
import json
import logging
import os
import re
import tempfile
import time
from pathlib import Path

import httpx
from telegram import BotCommand, Update
from telegram.error import BadRequest, RetryAfter
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from claude_runner import ClaudeRunner
from config import ALLOWED_BASE, GROQ_API_KEY, TELEGRAM_BOT_TOKEN, allowed_user_ids, validate
from scheduler import Scheduler
from skills import SKILLS, get_skill_prompt, list_skills
from utils import detect_created_files, markdown_to_tg_html, split_message

logging.basicConfig(
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

runner = ClaudeRunner()
scheduler_instance: Scheduler | None = None


# --- Auth ---

def is_authorized(user_id: int) -> bool:
    return user_id in allowed_user_ids()


def auth_check(func):
    """Decorator: silently ignore unauthorized users."""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.effective_user or not is_authorized(update.effective_user.id):
            return
        return await func(update, context)
    return wrapper


# --- Reply helpers ---

# Threshold for auto-attaching response as .md file
DOC_THRESHOLD = 1500


async def send_reply(message, text: str):
    """Send reply with HTML formatting, falling back to plain text per chunk."""
    formatted = markdown_to_tg_html(text)
    for chunk in split_message(formatted):
        try:
            await message.reply_text(chunk, parse_mode="HTML")
        except Exception:
            # Strip HTML tags and send as plain text
            plain = html.unescape(re.sub(r"<[^>]+>", "", chunk))
            await message.reply_text(plain)


def _looks_like_document(text: str) -> bool:
    """Check if a response looks like a formatted document."""
    headers = len(re.findall(r"^#{1,6}\s", text, re.MULTILINE))
    return len(text) > DOC_THRESHOLD and headers >= 2


async def send_as_file(message, text: str, filename: str = "response.md"):
    """Send text as a .md file attachment."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", prefix="claude_", delete=False
    ) as f:
        f.write(text)
        f.flush()
        await message.reply_document(
            document=open(f.name, "rb"),
            filename=filename,
            caption="Full document attached.",
        )
    os.unlink(f.name)


async def send_detected_files(message, files: list[Path]):
    """Send auto-detected files created by Claude."""
    for fp in files[:5]:  # Cap at 5 files
        try:
            await message.reply_document(
                document=open(fp, "rb"),
                filename=fp.name,
            )
        except Exception as e:
            await message.reply_text(f"Could not send {fp.name}: {e}")


# --- Streaming ---

class StreamingMessage:
    """Handles streaming responses — shows partial results as they arrive from multi-turn runs."""

    MAX_CHUNK = 4000

    def __init__(self, chat_id: int, bot):
        self.chat_id = chat_id
        self.bot = bot
        self.msg = None
        self.sent_len = 0  # chars sealed in previous messages
        self.last_edit = 0.0

    async def update(self, full_text: str):
        """Called with accumulated text. Updates Telegram message at most every 2s."""
        current = full_text[self.sent_len:]
        if not current.strip():
            return

        now = time.time()

        if self.msg is None:
            self.msg = await self.bot.send_message(
                self.chat_id, current[:self.MAX_CHUNK] + " ..."
            )
            self.last_edit = now
            return

        # Split if too long
        if len(current) > self.MAX_CHUNK:
            seal = current.rfind("\n", 0, self.MAX_CHUNK)
            if seal < self.MAX_CHUNK // 2:
                seal = self.MAX_CHUNK
            try:
                await self.msg.edit_text(current[:seal])
            except (BadRequest, RetryAfter):
                pass
            self.sent_len += seal
            remainder = current[seal:]
            self.msg = await self.bot.send_message(self.chat_id, remainder + " ...")
            self.last_edit = now
            return

        if now - self.last_edit < 2.0:
            return

        try:
            await self.msg.edit_text(current + " ...")
            self.last_edit = now
        except BadRequest:
            pass
        except RetryAfter as e:
            await asyncio.sleep(e.retry_after)

    async def show_status(self, status: str):
        """Show a tool/activity status line in the message."""
        if self.msg is None:
            self.msg = await self.bot.send_message(self.chat_id, status)
            self.last_edit = time.time()
        else:
            try:
                await self.msg.edit_text(status)
                self.last_edit = time.time()
            except BadRequest:
                pass

    async def finalize(self, full_text: str, footer: str = ""):
        """Final edit with HTML formatting + footer."""
        current = full_text[self.sent_len:]
        formatted = markdown_to_tg_html(current + footer)
        chunks = split_message(formatted)

        if self.msg is None:
            for chunk in chunks:
                try:
                    await self.bot.send_message(self.chat_id, chunk, parse_mode="HTML")
                except Exception:
                    plain = html.unescape(re.sub(r"<[^>]+>", "", chunk))
                    await self.bot.send_message(self.chat_id, plain)
            return

        try:
            await self.msg.edit_text(chunks[0], parse_mode="HTML")
        except Exception:
            try:
                plain = html.unescape(re.sub(r"<[^>]+>", "", chunks[0]))
                await self.msg.edit_text(plain)
            except Exception:
                pass

        for chunk in chunks[1:]:
            try:
                await self.bot.send_message(self.chat_id, chunk, parse_mode="HTML")
            except Exception:
                plain = html.unescape(re.sub(r"<[^>]+>", "", chunk))
                await self.bot.send_message(self.chat_id, plain)


# --- Typing indicator ---

class TypingIndicator:
    """Keep Telegram's 'typing...' bubble visible for the entire processing duration."""

    def __init__(self, bot, chat_id: int):
        self.bot = bot
        self.chat_id = chat_id
        self._task = None

    async def __aenter__(self):
        self._task = asyncio.create_task(self._loop())
        return self

    async def __aexit__(self, *args):
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass

    async def _loop(self):
        while True:
            try:
                await self.bot.send_chat_action(self.chat_id, "typing")
            except Exception:
                pass
            await asyncio.sleep(5)


# --- Tool status ---

def _tool_status(name: str, input_data: dict) -> str:
    """Format a tool_use event into a short status line."""
    if name == "Read":
        path = input_data.get("file_path", "")
        return f"Reading {Path(path).name}" if path else "Reading..."
    if name == "Bash":
        cmd = input_data.get("command", "")[:50]
        return f"$ {cmd}" if cmd else "Running command..."
    if name in ("Edit", "Write"):
        path = input_data.get("file_path", "")
        return f"Editing {Path(path).name}" if path else "Editing..."
    if name == "Glob":
        return f"Search: {input_data.get('pattern', '...')}"
    if name == "Grep":
        return f"Grep: {input_data.get('pattern', '...')}"
    if name == "WebSearch":
        return f"Searching: {input_data.get('query', '...')[:40]}"
    return f"{name}..."


# --- Voice ---

async def transcribe_voice(audio_path: Path) -> str:
    """Transcribe audio via Groq Whisper API."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.groq.com/openai/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            files={"file": ("audio.ogg", open(audio_path, "rb"), "audio/ogg")},
            data={"model": "whisper-large-v3"},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["text"]


# --- Commands ---

@auth_check
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    skill_lines = "\n".join(f"/{name} — {info['description']}" for name, info in SKILLS.items())
    await update.message.reply_text(
        "Claude Code bridge ready.\n\n"
        "Send a message or voice note to talk to Claude.\n\n"
        "Session:\n"
        "/project <path> — set working directory\n"
        "/projects — list available projects\n"
        "/new — clear session\n"
        "/status — current session info\n"
        "/permissions — toggle permission mode\n\n"
        "Scheduling:\n"
        "/schedule — schedule a recurring prompt\n"
        "/jobs — list scheduled jobs\n"
        "/canceljob — cancel a job\n\n"
        f"Skills:\n{skill_lines}\n"
        "/skills — list all skills\n\n"
        "/help — show this message"
    )


@auth_check
async def cmd_project(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /project <path>\nExample: /project polybaca")
        return

    raw = " ".join(context.args)
    # Allow both absolute and relative-to-Documents paths
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = ALLOWED_BASE / raw

    path = path.resolve()

    if not str(path).startswith(str(ALLOWED_BASE)):
        await update.message.reply_text(f"Path must be under {ALLOWED_BASE}")
        return

    if not path.is_dir():
        await update.message.reply_text(f"Not found: {path}")
        return

    runner.set_project(update.effective_user.id, path)
    await update.message.reply_text(f"Project: {path.name}\nSession cleared.")


@auth_check
async def cmd_projects(update: Update, context: ContextTypes.DEFAULT_TYPE):
    dirs = sorted(
        p.name for p in ALLOWED_BASE.iterdir()
        if p.is_dir() and not p.name.startswith(".")
    )
    if not dirs:
        await update.message.reply_text("No projects found.")
        return

    text = "Projects:\n" + "\n".join(f"  {d}" for d in dirs)
    await update.message.reply_text(text)


@auth_check
async def cmd_new(update: Update, context: ContextTypes.DEFAULT_TYPE):
    runner.clear_session(update.effective_user.id)
    await update.message.reply_text("Session cleared.")


@auth_check
async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = runner.get_session(update.effective_user.id)
    project = session.project_dir.name if session.project_dir else "None"
    has_session = "Yes" if session.session_id else "No"
    await update.message.reply_text(
        f"Project: {project}\n"
        f"Active session: {has_session}"
    )


# --- Backend commands (reimplemented CLI commands) ---

MODELS = {"sonnet", "opus", "haiku", "claude-sonnet-4-6", "claude-opus-4-6", "claude-haiku-4-5-20251001"}


@auth_check
async def cmd_cost(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = runner.get_session(update.effective_user.id)
    if session.message_count == 0:
        await update.message.reply_text("No messages in this session yet.")
        return
    await update.message.reply_text(
        f"Session cost: ${session.total_cost:.4f}\n"
        f"Total time: {session.total_duration:.1f}s\n"
        f"Messages: {session.message_count}"
    )


@auth_check
async def cmd_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = runner.get_session(update.effective_user.id)

    if not context.args:
        current = session.model or "default"
        await update.message.reply_text(
            f"Current model: {current}\n\n"
            f"Usage: /model <name>\n"
            f"Examples: /model opus, /model sonnet, /model haiku"
        )
        return

    model = context.args[0].lower()
    if model == "default":
        session.model = None
        await update.message.reply_text("Model reset to default.")
        return

    session.model = model
    await update.message.reply_text(f"Model set to: {model}")


@auth_check
async def cmd_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    config_path = Path.home() / ".claude" / "settings.json"
    if not config_path.is_file():
        await update.message.reply_text("No settings.json found.")
        return

    try:
        data = json.loads(config_path.read_text())
        text = json.dumps(data, indent=2)
        if len(text) > 4000:
            text = text[:4000] + "\n... (truncated)"
        await update.message.reply_text(f"~/.claude/settings.json:\n\n{text}")
    except Exception as e:
        await update.message.reply_text(f"Error reading config: {e}")


@auth_check
async def cmd_getfile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Download a file from the Mac Mini."""
    if not context.args:
        await update.message.reply_text("Usage: /getfile <path>\nExample: /getfile output/nda.md")
        return

    raw = " ".join(context.args)
    path = Path(raw).expanduser()

    # Resolve relative paths against project dir or ALLOWED_BASE
    if not path.is_absolute():
        session = runner.get_session(update.effective_user.id)
        base = session.project_dir or ALLOWED_BASE
        path = base / raw

    path = path.resolve()

    if not str(path).startswith(str(ALLOWED_BASE)):
        await update.message.reply_text(f"Path must be under {ALLOWED_BASE}")
        return

    if not path.is_file():
        await update.message.reply_text(f"Not found: {path}")
        return

    if path.stat().st_size > 20 * 1024 * 1024:
        await update.message.reply_text("File too large (>20 MB).")
        return

    await update.message.reply_document(
        document=open(path, "rb"),
        filename=path.name,
    )


# --- Permissions ---

@auth_check
async def cmd_permissions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = runner.get_session(update.effective_user.id)
    if session.permission_mode == "bypassPermissions":
        session.permission_mode = "acceptEdits"
        await update.message.reply_text("Mode: acceptEdits (safe — edits only)")
    else:
        session.permission_mode = "bypassPermissions"
        await update.message.reply_text("Mode: bypassPermissions (full access)")


# --- Scheduling ---

@auth_check
async def cmd_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or len(context.args) < 6:
        await update.message.reply_text(
            "Usage: /schedule <min> <hr> <day> <mon> <dow> <prompt>\n"
            "Example: /schedule */5 * * * * check disk usage"
        )
        return

    cron = " ".join(context.args[:5])
    prompt = " ".join(context.args[5:])
    session = runner.get_session(update.effective_user.id)
    project_dir = str(session.project_dir) if session.project_dir else None

    try:
        job = scheduler_instance.add(
            cron=cron,
            prompt=prompt,
            chat_id=update.effective_chat.id,
            user_id=update.effective_user.id,
            project_dir=project_dir,
        )
        await update.message.reply_text(f"Scheduled [{job.id}]: {cron}\n{prompt}")
    except Exception as e:
        await update.message.reply_text(f"Invalid schedule: {e}")


@auth_check
async def cmd_jobs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    jobs = scheduler_instance.list_jobs(update.effective_user.id)
    if not jobs:
        await update.message.reply_text("No scheduled jobs.")
        return

    lines = []
    for j in jobs:
        lines.append(f"[{j.id}] {j.cron}  {j.prompt[:60]}")
    await update.message.reply_text("Scheduled jobs:\n" + "\n".join(lines))


@auth_check
async def cmd_canceljob(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /canceljob <id>")
        return

    job_id = context.args[0]
    if scheduler_instance.remove(job_id):
        await update.message.reply_text(f"Cancelled job {job_id}.")
    else:
        await update.message.reply_text(f"Job {job_id} not found.")


# --- Skill commands ---

@auth_check
async def cmd_skills(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(list_skills())


@auth_check
async def cmd_skill(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generic handler for skill commands like /sync, /wrap, /review, etc."""
    command = update.message.text.split()[0].lstrip("/").split("@")[0]
    args = " ".join(context.args) if context.args else ""
    skill_info = SKILLS.get(command)

    if not skill_info:
        await update.message.reply_text(f"Unknown skill: /{command}\n\n{list_skills()}")
        return

    if skill_info.get("needs_project"):
        session = runner.get_session(update.effective_user.id)
        if not session.project_dir:
            await update.message.reply_text(
                f"/{command} requires a project. Set one first:\n/project <path>"
            )
            return

    prompt = get_skill_prompt(command, args)

    async with TypingIndicator(context.bot, update.effective_chat.id):
        result = await runner.run(update.effective_user.id, prompt)
    await _send_result(update, result)


# --- Message handler ---

@auth_check
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = update.message.text
    if not prompt:
        return

    streamer = StreamingMessage(update.effective_chat.id, context.bot)

    async def on_tool(name, input_data):
        await streamer.show_status(_tool_status(name, input_data))

    async with TypingIndicator(context.bot, update.effective_chat.id):
        result = await runner.run_streaming(
            update.effective_user.id, prompt, streamer.update, on_tool
        )
    await _send_streaming_result(update, streamer, result)


# --- Media handlers ---

MEDIA_DIR = Path(tempfile.gettempdir()) / "claude-tg-media"

# Map Telegram MIME types to file extensions
EXT_MAP = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "application/pdf": ".pdf",
    "text/plain": ".txt",
    "application/json": ".json",
    "text/csv": ".csv",
}


@auth_check
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photos sent to the bot — download and ask Claude to analyze."""
    photo = update.message.photo[-1]  # Highest resolution
    caption = update.message.caption or "Describe and analyze this image."

    MEDIA_DIR.mkdir(exist_ok=True)
    file = await context.bot.get_file(photo.file_id)
    path = MEDIA_DIR / f"{photo.file_unique_id}.jpg"
    await file.download_to_drive(path)

    prompt = (
        f"Read the image at {path} using your Read tool, then respond to this request:\n\n"
        f"{caption}"
    )

    async with TypingIndicator(context.bot, update.effective_chat.id):
        result = await runner.run(update.effective_user.id, prompt)
    await _send_result(update, result)

    path.unlink(missing_ok=True)


@auth_check
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle documents (PDFs, text files, etc.) sent to the bot."""
    doc = update.message.document
    caption = update.message.caption or f"Read and analyze this file: {doc.file_name}"

    # Determine extension
    ext = Path(doc.file_name).suffix if doc.file_name else EXT_MAP.get(doc.mime_type, "")
    if not ext:
        await update.message.reply_text(f"Unsupported file type: {doc.mime_type}")
        return

    MEDIA_DIR.mkdir(exist_ok=True)
    file = await context.bot.get_file(doc.file_id)
    path = MEDIA_DIR / f"{doc.file_unique_id}{ext}"
    await file.download_to_drive(path)

    prompt = (
        f"Read the file at {path} using your Read tool, then respond to this request:\n\n"
        f"{caption}"
    )

    async with TypingIndicator(context.bot, update.effective_chat.id):
        result = await runner.run(update.effective_user.id, prompt)
    await _send_result(update, result)

    path.unlink(missing_ok=True)


# --- Voice handler ---

@auth_check
async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle voice messages — transcribe via Groq Whisper, then send to Claude."""
    voice = update.message.voice or update.message.audio
    if not voice:
        return

    if not GROQ_API_KEY:
        await update.message.reply_text("Voice not configured — set GROQ_API_KEY.")
        return

    MEDIA_DIR.mkdir(exist_ok=True)
    file = await context.bot.get_file(voice.file_id)
    path = MEDIA_DIR / f"{voice.file_unique_id}.ogg"
    await file.download_to_drive(path)

    await context.bot.send_chat_action(update.effective_chat.id, "typing")

    try:
        text = await transcribe_voice(path)
    except Exception as e:
        await update.message.reply_text(f"Transcription failed: {e}")
        return
    finally:
        path.unlink(missing_ok=True)

    streamer = StreamingMessage(update.effective_chat.id, context.bot)

    async def on_tool(name, input_data):
        await streamer.show_status(_tool_status(name, input_data))

    async with TypingIndicator(context.bot, update.effective_chat.id):
        result = await runner.run_streaming(
            update.effective_user.id, text, streamer.update, on_tool
        )
    await _send_streaming_result(update, streamer, result)


async def _send_result(update: Update, result):
    """Send a ClaudeResult back to the user with formatting, files, etc."""
    user_id = update.effective_user.id

    # Persist session
    if result.session_id:
        session = runner.get_session(user_id)
        session.session_id = result.session_id

    # Build footer
    footer_parts = []
    if result.cost:
        footer_parts.append(f"${result.cost:.4f}")
    if result.duration:
        footer_parts.append(f"{result.duration:.1f}s")
    footer = f"\n\n[{' · '.join(footer_parts)}]" if footer_parts else ""

    text = result.text + footer

    # Send formatted text
    await send_reply(update.message, text)

    # Auto-attach as .md if response looks like a document
    if _looks_like_document(result.text):
        await send_as_file(update.message, result.text, "document.md")

    # Auto-send files created during this run
    if result.run_started:
        session = runner.get_session(user_id)
        files = detect_created_files(
            result.text, session.project_dir, result.run_started
        )
        if files:
            await send_detected_files(update.message, files)


async def _send_streaming_result(update: Update, streamer: StreamingMessage, result):
    """Finalize a streaming response — format, footer, files."""
    user_id = update.effective_user.id

    if result.session_id:
        session = runner.get_session(user_id)
        session.session_id = result.session_id

    # Build footer
    footer_parts = []
    if result.cost:
        footer_parts.append(f"${result.cost:.4f}")
    if result.duration:
        footer_parts.append(f"{result.duration:.1f}s")
    footer = f"\n\n[{' · '.join(footer_parts)}]" if footer_parts else ""

    await streamer.finalize(result.text, footer)

    # Auto-attach as .md if response looks like a document
    if _looks_like_document(result.text):
        await send_as_file(update.message, result.text, "document.md")

    # Auto-send files created during this run
    if result.run_started:
        session = runner.get_session(user_id)
        files = detect_created_files(
            result.text, session.project_dir, result.run_started
        )
        if files:
            await send_detected_files(update.message, files)


# --- Main ---

def main():
    validate()
    logger.info("Starting Claude TG bridge...")

    # Explicitly set proxy for httpx if available (env vars alone are unreliable)
    proxy = os.environ.get("all_proxy") or os.environ.get("ALL_PROXY")
    builder = Application.builder().token(TELEGRAM_BOT_TOKEN)
    if proxy:
        logger.info("Using proxy: %s", proxy)
        builder = builder.proxy(proxy).get_updates_proxy(proxy)
    app = builder.build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_start))
    app.add_handler(CommandHandler("project", cmd_project))
    app.add_handler(CommandHandler("projects", cmd_projects))
    app.add_handler(CommandHandler("new", cmd_new))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("cost", cmd_cost))
    app.add_handler(CommandHandler("model", cmd_model))
    app.add_handler(CommandHandler("config", cmd_config))
    app.add_handler(CommandHandler("getfile", cmd_getfile))
    app.add_handler(CommandHandler("permissions", cmd_permissions))
    app.add_handler(CommandHandler("schedule", cmd_schedule))
    app.add_handler(CommandHandler("jobs", cmd_jobs))
    app.add_handler(CommandHandler("canceljob", cmd_canceljob))
    app.add_handler(CommandHandler("skills", cmd_skills))
    for skill_name in SKILLS:
        app.add_handler(CommandHandler(skill_name, cmd_skill))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    # Register command menu with Telegram (max 100 commands)
    async def post_init(application):
        global scheduler_instance
        scheduler_instance = Scheduler(runner, application.bot)
        scheduler_instance.start()

        commands = [
            BotCommand("project", "Set working directory"),
            BotCommand("projects", "List available projects"),
            BotCommand("new", "Clear session"),
            BotCommand("status", "Current session info"),
            BotCommand("cost", "Session cost & usage"),
            BotCommand("model", "Switch AI model"),
            BotCommand("permissions", "Toggle permission mode"),
            BotCommand("schedule", "Schedule a recurring prompt"),
            BotCommand("jobs", "List scheduled jobs"),
            BotCommand("canceljob", "Cancel a scheduled job"),
            BotCommand("config", "View Claude settings"),
            BotCommand("getfile", "Download a file"),
        ]
        # Add all skills to command menu
        for name, info in SKILLS.items():
            commands.append(BotCommand(name, info["description"][:256]))
        commands.append(BotCommand("skills", "List all skills"))
        commands.append(BotCommand("help", "Show help"))
        await application.bot.set_my_commands(commands)
        logger.info("Registered %d bot commands", len(commands))

    app.post_init = post_init
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
