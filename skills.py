"""Skill auto-discovery — loads all Claude Code skills/commands at startup."""

import os
import re
from pathlib import Path

CLAUDE_DIR = Path.home() / ".claude"

# Telegram bot commands: 1-32 chars, lowercase a-z, 0-9, underscore only
_VALID_CMD = re.compile(r"^[a-z0-9_]{1,32}$")

# Built-in CLI commands that don't work through claude -p
CLI_ONLY = {
    "login": "Authenticate Claude Code (CLI only)",
    "logout": "Sign out of Claude Code (CLI only)",
    "doctor": "Diagnose Claude Code issues (CLI only)",
    "compact": "Compress conversation context (CLI only)",
    "config": "View/edit Claude Code config (CLI only)",
    "model": "Switch AI model (CLI only)",
    "cost": "Show session costs (CLI only)",
    "permissions": "Manage tool permissions (CLI only)",
    "mcp": "Manage MCP servers (CLI only)",
    "init": "Initialize project settings (CLI only)",
    "vim": "Toggle vim mode (CLI only)",
}

# Custom prompt overrides for skills that need special handling
PROMPT_OVERRIDES = {}


def _note_prompt(args: str) -> str:
    api_key = os.getenv("NOTION_API_KEY", "")
    page_id = os.getenv("NOTION_IDEAS_PAGE", "316b1432-769f-808d-874a-c25219974335")
    return f"""Capture the following idea and save it to Notion.

Create a new page under the Ideas parent page (ID: {page_id}) using curl:

```
curl -s -X POST https://api.notion.com/v1/pages \\
  -H "Authorization: Bearer {api_key}" \\
  -H "Notion-Version: 2022-06-28" \\
  -H "Content-Type: application/json" \\
  -d '<json payload>'
```

Idea to capture: {args}

Format the page with: title, date, summary bullets, and action items if applicable. Confirm the page URL when done."""


PROMPT_OVERRIDES["note"] = _note_prompt


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Parse YAML frontmatter and return (metadata, body)."""
    if not text.startswith("---"):
        return {}, text

    end = text.find("---", 3)
    if end == -1:
        return {}, text

    fm = text[3:end].strip()
    body = text[end + 3:].strip()
    meta = {}
    for line in fm.split("\n"):
        if ":" in line:
            key, _, val = line.partition(":")
            meta[key.strip()] = val.strip().strip('"').strip("'")
    return meta, body


def _normalize_cmd(name: str) -> str | None:
    """Normalize a command name for Telegram (lowercase, underscores, 1-32 chars)."""
    name = name.lower().replace("-", "_")
    return name if _VALID_CMD.match(name) else None


def _discover_skills() -> dict:
    """Auto-discover all skills and commands from ~/.claude/."""
    skills = {}

    # 1. Custom skills: ~/.claude/skills/*/SKILL.md
    skills_dir = CLAUDE_DIR / "skills"
    if skills_dir.is_dir():
        for skill_dir in sorted(skills_dir.iterdir()):
            skill_file = skill_dir / "SKILL.md"
            if skill_file.is_file():
                text = skill_file.read_text()
                meta, body = _parse_frontmatter(text)
                raw_name = meta.get("name", skill_dir.name)
                name = _normalize_cmd(raw_name)
                if not name:
                    continue
                desc = meta.get("description", f"Run {name} skill")
                needs_project = "Bash" in meta.get("allowed-tools", "")
                skills[name] = {
                    "description": desc,
                    "needs_project": needs_project,
                    "prompt": body,
                    "source": str(skill_file),
                }

    # 2. Custom commands: ~/.claude/commands/*.md
    cmds_dir = CLAUDE_DIR / "commands"
    if cmds_dir.is_dir():
        for cmd_file in sorted(cmds_dir.glob("*.md")):
            text = cmd_file.read_text()
            meta, body = _parse_frontmatter(text)
            name = _normalize_cmd(cmd_file.stem)
            if not name:
                continue
            desc = meta.get("description", body.split("\n")[0][:100])
            skills[name] = {
                "description": desc,
                "needs_project": False,
                "prompt": body,
                "source": str(cmd_file),
            }

    # 3. Plugin commands: ~/.claude/plugins/**/commands/*.md
    plugins_dir = CLAUDE_DIR / "plugins"
    if plugins_dir.is_dir():
        for cmd_file in sorted(plugins_dir.rglob("commands/*.md")):
            text = cmd_file.read_text()
            meta, body = _parse_frontmatter(text)
            name = _normalize_cmd(cmd_file.stem)
            if not name:
                continue
            # Skip if name conflicts with a custom skill (custom takes priority)
            if name in skills:
                continue
            # Skip generic help files
            if name == "help":
                continue
            desc = meta.get("description", f"Run {name}")
            skills[name] = {
                "description": desc,
                "needs_project": True,
                "prompt": body,
                "source": str(cmd_file),
            }

    return skills


# Load at import time
SKILLS = _discover_skills()


def get_skill_prompt(name: str, args: str = "") -> str | None:
    if name in CLI_ONLY:
        return None

    # Check for custom prompt override (e.g. note)
    if name in PROMPT_OVERRIDES:
        return PROMPT_OVERRIDES[name](args or "")

    skill = SKILLS.get(name)
    if not skill:
        return None
    prompt = skill["prompt"]
    if args:
        return f"{prompt}\n\nTask: {args}"
    return prompt


def list_skills() -> str:
    lines = ["Skills (run via Telegram):\n"]
    for name, info in SKILLS.items():
        lines.append(f"  /{name} — {info['description']}")
    lines.append("\nCLI only (use in terminal):\n")
    for name, desc in CLI_ONLY.items():
        lines.append(f"  /{name} — {desc}")
    return "\n".join(lines)
