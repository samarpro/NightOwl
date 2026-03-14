"""Platform-specific message formatting.

Converts LLM markdown output to each channel's native rich text format.
The LLM produces standard markdown (bold, italic, code, headers, lists).
Each renderer translates to the platform's supported markup.
"""

from __future__ import annotations

import re


def _escape_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def markdown_to_telegram_html(text: str) -> str:
    """Convert markdown to Telegram-compatible HTML.

    Telegram supports: <b>, <i>, <code>, <pre>, <a href>, <s>, <u>
    """
    # Escape HTML entities first (but preserve our later insertions)
    # Work with code blocks first to avoid double-processing their contents

    # Fenced code blocks: ```lang\ncode\n``` → <pre>code</pre>
    def _replace_code_block(m: re.Match) -> str:
        code = _escape_html(m.group(2))
        return f"<pre>{code}</pre>"

    text = re.sub(r"```(\w*)\n?(.*?)```", _replace_code_block, text, flags=re.DOTALL)

    # Inline code: `code` → <code>code</code>
    def _replace_inline_code(m: re.Match) -> str:
        return f"<code>{_escape_html(m.group(1))}</code>"

    text = re.sub(r"`([^`]+)`", _replace_inline_code, text)

    # Now escape HTML in the remaining non-code text
    # Split on <pre>/<code> tags to avoid double-escaping
    parts = re.split(r"(</?(?:pre|code)>)", text)
    in_tag = False
    for i, part in enumerate(parts):
        if part in ("<pre>", "<code>"):
            in_tag = True
        elif part in ("</pre>", "</code>"):
            in_tag = False
        elif not in_tag:
            parts[i] = _escape_html(part)
    text = "".join(parts)

    # Headers: # Header → <b>Header</b>
    text = re.sub(r"^#{1,6}\s+(.+)$", r"<b>\1</b>", text, flags=re.MULTILINE)

    # Bold: **text** or __text__ → <b>text</b>
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"__(.+?)__", r"<b>\1</b>", text)

    # Italic: *text* or _text_ → <i>text</i>  (but not inside words)
    text = re.sub(r"(?<!\w)\*([^*]+?)\*(?!\w)", r"<i>\1</i>", text)
    text = re.sub(r"(?<!\w)_([^_]+?)_(?!\w)", r"<i>\1</i>", text)

    # Strikethrough: ~~text~~ → <s>text</s>
    text = re.sub(r"~~(.+?)~~", r"<s>\1</s>", text)

    # Links: [text](url) → <a href="url">text</a>
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)

    # Bullet lists: - item or * item → • item
    text = re.sub(r"^[\-\*]\s+", "• ", text, flags=re.MULTILINE)

    # Numbered lists: keep as-is (Telegram renders them fine)

    # Blockquotes: > text → (Telegram doesn't support, just indent)
    text = re.sub(r"^>\s+(.+)$", r"┃ \1", text, flags=re.MULTILINE)

    # Horizontal rules: --- or *** → ─────
    text = re.sub(r"^[\-\*]{3,}$", "─────────────────", text, flags=re.MULTILINE)

    return text.strip()


def markdown_to_whatsapp(text: str) -> str:
    """Convert markdown to WhatsApp native formatting.

    WhatsApp supports: *bold*, _italic_, ~strikethrough~, ```code```
    """
    # Fenced code blocks → WhatsApp code blocks (triple backtick)
    text = re.sub(r"```\w*\n?(.*?)```", r"```\1```", text, flags=re.DOTALL)

    # Headers → bold
    text = re.sub(r"^#{1,6}\s+(.+)$", r"*\1*", text, flags=re.MULTILINE)

    # Bold: **text** → *text*
    text = re.sub(r"\*\*(.+?)\*\*", r"*\1*", text)
    # __text__ → *text*
    text = re.sub(r"__(.+?)__", r"*\1*", text)

    # Italic: _text_ stays as-is (WhatsApp native)
    # But *text* for italic needs to not conflict with bold
    # Markdown single * italic → WhatsApp _italic_
    text = re.sub(r"(?<!\w)\*([^*]+?)\*(?!\w)", r"_\1_", text)

    # Strikethrough: ~~text~~ → ~text~
    text = re.sub(r"~~(.+?)~~", r"~\1~", text)

    # Links: [text](url) → text (url)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", text)

    # Bullet lists
    text = re.sub(r"^[\-\*]\s+", "• ", text, flags=re.MULTILINE)

    # Blockquotes
    text = re.sub(r"^>\s+(.+)$", r"┃ \1", text, flags=re.MULTILINE)

    # Horizontal rules
    text = re.sub(r"^[\-\*]{3,}$", "─────────────────", text, flags=re.MULTILINE)

    return text.strip()


def markdown_to_plaintext(text: str) -> str:
    """Convert markdown to clean plain text with Unicode structure.

    For SMS and other channels with no formatting support.
    """
    # Code blocks → indented
    def _indent_code(m: re.Match) -> str:
        lines = m.group(1).strip().splitlines()
        return "\n".join(f"  {line}" for line in lines)

    text = re.sub(r"```\w*\n?(.*?)```", _indent_code, text, flags=re.DOTALL)

    # Inline code → just the text
    text = re.sub(r"`([^`]+)`", r"\1", text)

    # Headers → UPPERCASE with underline
    def _header(m: re.Match) -> str:
        return f"{m.group(1).upper()}"

    text = re.sub(r"^#{1,6}\s+(.+)$", _header, text, flags=re.MULTILINE)

    # Bold/italic markers → stripped
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"__(.+?)__", r"\1", text)
    text = re.sub(r"(?<!\w)\*([^*]+?)\*(?!\w)", r"\1", text)
    text = re.sub(r"(?<!\w)_([^_]+?)_(?!\w)", r"\1", text)
    text = re.sub(r"~~(.+?)~~", r"\1", text)

    # Links
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", text)

    # Bullets
    text = re.sub(r"^[\-\*]\s+", "• ", text, flags=re.MULTILINE)

    # Blockquotes
    text = re.sub(r"^>\s+(.+)$", r"| \1", text, flags=re.MULTILINE)

    # Horizontal rules
    text = re.sub(r"^[\-\*]{3,}$", "───────────", text, flags=re.MULTILINE)

    return text.strip()
