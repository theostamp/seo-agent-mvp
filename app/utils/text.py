import re
from html import unescape


TAG_RE = re.compile(r"<[^>]+>")
WHITESPACE_RE = re.compile(r"\s+")


def strip_html(value: str) -> str:
    if not value:
        return ""
    text = TAG_RE.sub(" ", value)
    text = unescape(text)
    text = WHITESPACE_RE.sub(" ", text).strip()
    return text


def truncate(text: str, max_length: int) -> str:
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."
