"""Skill definitions — maps Telegram commands to Claude Code skill prompts."""

import os

SKILLS = {
    "sync": {
        "description": "Pull latest, check tasks & git status",
        "needs_project": True,
        "prompt": """Session start sync. Run these steps in order:

1. Run `git pull`. If not a git repo, skip.
2. Read `tasks/todo.md` if it exists — summarize what's done, in progress, blocked.
3. Read `tasks/lessons.md` if it exists — note past mistakes.
4. Run `git log --oneline -10` and `git status`.
5. Report: current branch, recent commits, open tasks, lessons, any WIP work.""",
    },
    "wrap": {
        "description": "Commit, push, update tasks",
        "needs_project": True,
        "prompt": """End-of-session wrap-up. Run these steps in order:

1. Run `git status` and `git diff --stat` to see all changes.
2. Commit changes: if complete, use a clear message. If incomplete, use `wip:` prefix. Stage selectively — never `git add .`. Never commit secrets or .env files.
3. Push to remote. If no upstream, set it with `git push -u origin <branch>`.
4. Read and update `tasks/todo.md`: mark completed items, note in-progress and blocked.
5. Report: commits pushed, task status changes, anything left for next session.""",
    },
    "review": {
        "description": "Self-review recent code changes",
        "needs_project": True,
        "prompt": """Review recent code changes:

1. Check uncommitted changes with `git diff` and `git diff --cached`. If none, review last commit with `git diff HEAD~1`.
2. Read every changed file in full.
3. Check for: logic errors, security issues (hardcoded secrets, injection), type safety, race conditions, dead code, over-engineering.
4. Report findings grouped by severity (critical > high > medium > low). For each: file, line, issue, fix. If no issues, say so.""",
    },
    "backup": {
        "description": "Backup Claude global settings to GitHub",
        "needs_project": False,
        "prompt": """Run the Claude global settings backup script:

```bash
bash ~/Documents/claude-global-backup/sync.sh
```

Report whether files were changed and pushed, or already up to date.""",
    },
    "note": {
        "description": "Save ideas to Notion",
        "needs_project": False,
    },
}


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


def get_skill_prompt(name: str, args: str = "") -> str | None:
    skill = SKILLS.get(name)
    if not skill:
        return None
    if name == "note":
        return _note_prompt(args or "general ideas from this conversation")
    prompt = skill["prompt"]
    if args:
        return f"{prompt}\n\nContext: {args}"
    return prompt


def list_skills() -> str:
    lines = ["Available skills:\n"]
    for name, info in SKILLS.items():
        lines.append(f"  /{name} — {info['description']}")
    return "\n".join(lines)
