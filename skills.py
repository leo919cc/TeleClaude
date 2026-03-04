"""Skill definitions — maps Telegram commands to Claude Code skill prompts."""

import os

SKILLS = {
    # --- Session management ---
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
    # --- Git commands ---
    "commit": {
        "description": "Create a git commit",
        "needs_project": True,
        "prompt": """Check `git status`, `git diff HEAD`, `git branch --show-current`, and `git log --oneline -10`.
Based on the changes, stage relevant files and create a single git commit with an appropriate message. Never commit secrets or .env files.""",
    },
    "commitpr": {
        "description": "Commit, push, and open a PR",
        "needs_project": True,
        "prompt": """Check `git status`, `git diff HEAD`, and `git branch --show-current`.
Based on the changes:
1. Create a new branch if on main.
2. Stage and commit with an appropriate message.
3. Push the branch to origin.
4. Create a pull request using `gh pr create`.""",
    },
    # --- Code review ---
    "review": {
        "description": "Self-review recent code changes",
        "needs_project": True,
        "prompt": """Review recent code changes:

1. Check uncommitted changes with `git diff` and `git diff --cached`. If none, review last commit with `git diff HEAD~1`.
2. Read every changed file in full.
3. Check for: logic errors, security issues (hardcoded secrets, injection), type safety, race conditions, dead code, over-engineering.
4. Report findings grouped by severity (critical > high > medium > low). For each: file, line, issue, fix. If no issues, say so.""",
    },
    "codex": {
        "description": "Cross-model code review via Codex",
        "needs_project": True,
        "prompt": """Cross-model code review using PAL codereview with gpt-5.1-codex. Max 3 rounds.

1. Identify changed files: uncommitted changes or last commit.
2. Read every changed file in full.
3. Run the project's type checker if applicable (tsc, pyright, go build).
4. Call mcp__pal__codereview with review_type "full", the changed file paths, context of what changed, and your preliminary assessment. Scope: logic bugs, edge cases, type safety, race conditions, security. Exclude: style, formatting, naming.
5. For each finding: fix if you agree, reject with reasoning if you disagree.
6. Re-review if fixes were made (max 3 rounds).
7. Report: total rounds, issues found/fixed/rejected/deferred.""",
    },
    "codereview": {
        "description": "Review a pull request",
        "needs_project": True,
        "prompt": """Review the current pull request:

1. Check if a PR exists: `gh pr view`. If not, report and stop.
2. Get the PR diff: `gh pr diff`.
3. Read the changed files in full.
4. Check for: bugs, CLAUDE.md compliance, security issues, error handling, test coverage.
5. Post a comment on the PR with findings using `gh pr comment`. Format: list issues with file:line references, grouped by severity. If no issues, say so.""",
    },
    "reviewpr": {
        "description": "Comprehensive PR review with multiple checks",
        "needs_project": True,
        "prompt": """Comprehensive PR review. Check git diff for changed files.

Review for these aspects:
1. Code quality — CLAUDE.md compliance, bugs, patterns
2. Error handling — silent failures, missing catch blocks
3. Test coverage — are changes tested?
4. Simplicity — over-engineering, dead code, unnecessary complexity

Report findings grouped as:
- Critical Issues (must fix before merge)
- Important Issues (should fix)
- Suggestions (nice to have)
- Strengths (what's well-done)

Include file:line references for each finding.""",
    },
    # --- Planning & development ---
    "plan": {
        "description": "Create or update task plan",
        "needs_project": True,
        "prompt_with_args": True,
        "prompt": """Create a structured task plan in `tasks/todo.md`.

1. Explore the codebase to understand what exists.
2. Break the work into concrete steps, ordered by dependency.
3. Write the plan to `tasks/todo.md` (create `tasks/` dir if needed). If it already exists, update rather than overwrite.
4. Use format: Context section, Plan with checkboxes, Notes with trade-offs.
5. Present the plan for confirmation.""",
    },
    "feature": {
        "description": "Guided feature development",
        "needs_project": True,
        "prompt_with_args": True,
        "prompt": """Guided feature development:

1. Explore the codebase to understand relevant patterns and architecture.
2. Identify all ambiguities and edge cases — list clarifying questions.
3. Design an implementation approach: minimal changes, clean architecture, trade-offs.
4. Present the approach and wait for confirmation before implementing.
5. Implement following codebase conventions.
6. Self-review for simplicity, bugs, and correctness.
7. Summarize: what was built, files modified, key decisions, next steps.""",
    },
    # --- Utilities ---
    "revise": {
        "description": "Update CLAUDE.md with session learnings",
        "needs_project": True,
        "prompt": """Review this session for learnings about working in this codebase. Update CLAUDE.md with useful context for future sessions.

1. Reflect: what commands, patterns, quirks, or gotchas were discovered?
2. Find CLAUDE.md files in the project.
3. Draft concise additions (one line per concept). Avoid verbose explanations.
4. Show proposed changes as diffs.
5. Apply the changes.""",
    },
    "backup": {
        "description": "Backup Claude settings to GitHub",
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
        return f"{prompt}\n\nTask: {args}"
    return prompt


def list_skills() -> str:
    lines = ["Available skills:\n"]
    for name, info in SKILLS.items():
        lines.append(f"  /{name} — {info['description']}")
    return "\n".join(lines)
