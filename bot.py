"""Telegram → Claude Code bridge bot."""

import logging
import os

from telegram import Update
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
from utils import split_message

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


# --- Commands ---

@auth_check
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Claude Code bridge ready.\n\n"
        "Just send a message to talk to Claude.\n\n"
        "/project <path> — set working directory\n"
        "/projects — list available projects\n"
        "/new — clear session\n"
        "/status — current session info\n"
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


# --- Message handler ---

@auth_check
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = update.message.text
    if not prompt:
        return

    await context.bot.send_chat_action(update.effective_chat.id, "typing")

    result = await runner.run(update.effective_user.id, prompt)

    # Persist session ID for continuity
    if result.session_id:
        session = runner.get_session(update.effective_user.id)
        session.session_id = result.session_id

    # Build footer
    footer_parts = []
    if result.cost:
        footer_parts.append(f"${result.cost:.4f}")
    if result.duration:
        footer_parts.append(f"{result.duration:.1f}s")
    footer = f"\n\n[{' · '.join(footer_parts)}]" if footer_parts else ""

    text = result.text + footer
    chunks = split_message(text)

    for chunk in chunks:
        await update.message.reply_text(chunk)


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
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
