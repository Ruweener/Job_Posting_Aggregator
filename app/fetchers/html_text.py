"""Turn job-description HTML into plain text, using only the standard library."""
import html
import re
from html.parser import HTMLParser

# Tags that start a new line of text when they open or close
_BLOCK_TAGS = {"p", "div", "br", "li", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6", "tr"}


class _TextExtractor(HTMLParser):
    """HTMLParser calls these methods as it walks the HTML; we keep only the text."""

    def __init__(self):
        super().__init__(convert_charrefs=True)  # decodes &amp; &nbsp; etc. in text
        self.parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in _BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in _BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data):
        self.parts.append(data)


def html_to_text(raw: str | None) -> str | None:
    if not raw:
        return None
    # Greenhouse double-encodes: the HTML itself arrives as "&lt;p&gt;...". Unescape once
    # to get real tags, then let the parser strip them.
    parser = _TextExtractor()
    parser.feed(html.unescape(raw))
    text = "".join(parser.parts).replace("\xa0", " ")  # \xa0 = non-breaking space
    text = re.sub(r"[ \t]+", " ", text)          # collapse runs of spaces
    text = re.sub(r"\s*\n\s*", "\n", text)       # one newline between lines
    return text.strip() or None
