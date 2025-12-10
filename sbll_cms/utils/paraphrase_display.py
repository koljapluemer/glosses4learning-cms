from __future__ import annotations

PARAPHRASE_TAG = "eng:paraphrase"


def paraphrase_display(content: str | object, tags: list[str] | None = None) -> str:
    """Wrap content in brackets when a paraphrase tag is present."""
    tag_list = tags
    text = content
    if hasattr(content, "content"):
        text = getattr(content, "content")
        tag_list = tags or getattr(content, "tags", [])
    if tag_list and PARAPHRASE_TAG in tag_list:
        return f"[{text}]"
    return str(text)
