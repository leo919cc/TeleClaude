"""Telegram → Claude Code bridge bot."""

import html
import json
import logging
import os
import re
import tempfile
from pathlib import Path

from telegram import BotCommand, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from telegram.request import HTTPXRequest

from claude_runner import ClaudeRunner
from config import ALLOWED_BASE, TELEGRAM_BOT_TOKEN, allowed_user_ids, validate
from skills import SKILLS, get_skill_prompt, list_skills
from utils import detect_created_files, markdown_to_tg_html, split_message

logging.basicConfig(
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

runner = ClaudeRunner()


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


# --- Commands ---

@auth_check
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    skill_lines = "\n".join(f"/{name} — {info['description']}" for name, info in SKILLS.items())
    await update.message.reply_text(
        "Claude Code bridge ready.\n\n"
        "Send a message to talk to Claude.\n\n"
        "Session:\n"
        "/project <path> — set working directory\n"
        "/projects — list available projects\n"
        "/new — clear session\n"
        "/status — current session info\n\n"
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
    await context.bot.send_chat_action(update.effective_chat.id, "typing")

    result = await runner.run(update.effective_user.id, prompt)
    await _send_result(update, result)


# --- Message handler ---

@auth_check
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = update.message.text
    if not prompt:
        return

    await context.bot.send_chat_action(update.effective_chat.id, "typing")

    result = await runner.run(update.effective_user.id, prompt)
    await _send_result(update, result)


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
    app.add_handler(CommandHandler("skills", cmd_skills))
    for skill_name in SKILLS:
        app.add_handler(CommandHandler(skill_name, cmd_skill))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Register command menu with Telegram (max 100 commands)
    async def post_init(application):
        commands = [
            BotCommand("project", "Set working directory"),
            BotCommand("projects", "List available projects"),
            BotCommand("new", "Clear session"),
            BotCommand("status", "Current session info"),
            BotCommand("cost", "Session cost & usage"),
            BotCommand("model", "Switch AI model"),
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
