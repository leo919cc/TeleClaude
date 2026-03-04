"""Telegram → Claude Code bridge bot."""

import logging
import os

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
from skills import CLI_ONLY, SKILLS, get_skill_prompt, list_skills
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


# --- Skill commands ---

@auth_check
async def cmd_cli_only(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reply when someone tries to use a CLI-only command via Telegram."""
    command = update.message.text.split()[0].lstrip("/").split("@")[0]
    desc = CLI_ONLY.get(command, "")
    await update.message.reply_text(
        f"/{command} is only available in the Claude Code terminal.\n\n{desc}"
    )


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

    if result.session_id:
        session = runner.get_session(update.effective_user.id)
        session.session_id = result.session_id

    footer_parts = []
    if result.cost:
        footer_parts.append(f"${result.cost:.4f}")
    if result.duration:
        footer_parts.append(f"{result.duration:.1f}s")
    footer = f"\n\n[{' · '.join(footer_parts)}]" if footer_parts else ""

    text = result.text + footer
    for chunk in split_message(text):
        await update.message.reply_text(chunk)


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
    app.add_handler(CommandHandler("skills", cmd_skills))
    for skill_name in SKILLS:
        app.add_handler(CommandHandler(skill_name, cmd_skill))
    for cli_name in CLI_ONLY:
        app.add_handler(CommandHandler(cli_name, cmd_cli_only))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Register command menu with Telegram (max 100 commands)
    async def post_init(application):
        commands = [
            BotCommand("project", "Set working directory"),
            BotCommand("projects", "List available projects"),
            BotCommand("new", "Clear session"),
            BotCommand("status", "Current session info"),
        ]
        # Add all skills to command menu
        for name, info in SKILLS.items():
            commands.append(BotCommand(name, info["description"][:256]))
        # Add CLI-only commands (flagged)
        for name, desc in CLI_ONLY.items():
            commands.append(BotCommand(name, desc[:256]))
        commands.append(BotCommand("skills", "List all skills"))
        commands.append(BotCommand("help", "Show help"))
        await application.bot.set_my_commands(commands)
        logger.info("Registered %d bot commands", len(commands))

    app.post_init = post_init
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
