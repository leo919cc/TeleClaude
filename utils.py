"""Utilities — message splitting, Markdown→HTML conversion, file detection."""

import html
import re
import time
from pathlib import Path

MAX_LENGTH = 4096

# Max file size to auto-send via Telegram (20 MB)
MAX_FILE_SIZE = 20 * 1024 * 1024


def split_message(text: str) -> list[str]:
    """Split text into chunks that fit Telegram's message limit.

    Tries to split at newlines first, then at spaces, then hard-cuts.
    """
    if len(text) <= MAX_LENGTH:
        return [text]

    chunks = []
    while text:
        if len(text) <= MAX_LENGTH:
            chunks.append(text)
            break

        # Try to find a newline to split at
        cut = text.rfind("\n", 0, MAX_LENGTH)
        if cut == -1 or cut < MAX_LENGTH // 2:
            # Try space
            cut = text.rfind(" ", 0, MAX_LENGTH)
        if cut == -1 or cut < MAX_LENGTH // 2:
            # Hard cut
            cut = MAX_LENGTH

        chunks.append(text[:cut])
        text = text[cut:].lstrip("\n")

    return chunks


def markdown_to_tg_html(text: str) -> str:
    """Best-effort Markdown → Telegram HTML conversion."""
    placeholders: list[str] = []

    def _hold(content: str) -> str:
        idx = len(placeholders)
        placeholders.append(content)
        return f"\x00PH{idx}\x00"

    # 1. Protect fenced code blocks
    def _fenced(m):
        lang = m.group(1) or ""
        code = html.escape(m.group(2).strip())
        if lang:
            return _hold(f'<pre><code class="language-{lang}">{code}</code></pre>')
        return _hold(f"<pre>{code}</pre>")

    text = re.sub(r"```(\w*)\n(.*?)```", _fenced, text, flags=re.DOTALL)

    # 2. Protect inline code
    def _inline(m):
        return _hold(f"<code>{html.escape(m.group(1))}</code>")

    text = re.sub(r"`([^`\n]+)`", _inline, text)

    # 3. Protect markdown links
    link_pairs: list[tuple[str, str]] = []

    def _link(m):
        idx = len(link_pairs)
        link_pairs.append((m.group(1), m.group(2)))
        return f"\x00LK{idx}\x00"

    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", _link, text)

    # 4. Escape HTML entities in remaining text
    text = html.escape(text, quote=False)

    # 5. Convert markdown formatting
    # Headers → bold
    text = re.sub(r"^#{1,6}\s+(.+)$", r"<b>\1</b>", text, flags=re.MULTILINE)
    # Bold
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"__(.+?)__", r"<b>\1</b>", text)
    # Italic
    text = re.sub(r"(?<!\*)\*([^*\n]+?)\*(?!\*)", r"<i>\1</i>", text)
    # Blockquotes (> already escaped to &gt;)
    text = re.sub(r"^&gt;\s?(.+)$", r"<blockquote>\1</blockquote>", text, flags=re.MULTILINE)
    # Horizontal rules
    text = re.sub(r"^-{3,}$", "—" * 15, text, flags=re.MULTILINE)
    text = re.sub(r"^\*{3,}$", "—" * 15, text, flags=re.MULTILINE)
    # Clean escaped underscores from markdown
    text = text.replace("\\_", "_")

    # 6. Restore protected elements
    for idx, content in enumerate(placeholders):
        text = text.replace(f"\x00PH{idx}\x00", content)
    for idx, (link_text, url) in enumerate(link_pairs):
        text = text.replace(
            f"\x00LK{idx}\x00",
            f'<a href="{html.escape(url)}">{html.escape(link_text)}</a>',
        )

    return text


def detect_created_files(
    text: str, project_dir: Path | None, since: float
) -> list[Path]:
    """Find file paths mentioned in text that were created/modified after `since`."""
    found: list[Path] = []
    seen: set[str] = set()

    # Extract paths from backticks and bare absolute paths
    candidates: list[str] = re.findall(r"`(/[^`\s]+)`", text)
    candidates += re.findall(r"`(\./[^`\s]+)`", text)
    candidates += re.findall(r"`([^`\s]+\.\w{1,6})`", text)
    candidates += re.findall(r"(?:^|\s)(/\S+\.\w{1,10})", text, re.MULTILINE)

    for raw in candidates:
        if raw in seen:
            continue
        seen.add(raw)

        p = Path(raw).expanduser()
        if not p.is_absolute() and project_dir:
            p = project_dir / raw

        try:
            p = p.resolve()
            if p.is_file() and p.stat().st_mtime >= since and p.stat().st_size <= MAX_FILE_SIZE:
                found.append(p)
        except (OSError, ValueError):
            continue

    return found
