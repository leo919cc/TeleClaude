"""Utilities — message splitting for Telegram's 4096 char limit."""

MAX_LENGTH = 4096


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
