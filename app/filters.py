"""Small, pure functions that classify postings. No I/O, so they are easy to test."""
import re

# \b is a word boundary, so "intern" matches "Intern," but not "International" or "Internal".
# co-?op matches "co-op" and "coop". The intern(s|ship)? group covers "interns" and "internship".
_INTERN_RE = re.compile(r"\b(intern(s|ship)?|co-?op|student)\b", re.IGNORECASE)


def is_internship(title: str, employment_type: str | None = None) -> bool:
    """True if the title, or the board's own job-type label, says internship / co-op / student."""
    if _INTERN_RE.search(title):
        return True
    return bool(employment_type and _INTERN_RE.search(employment_type))


# Months map to the term they start: Jan-Apr Winter, May-Aug Summer, Sep-Dec Fall.
_MONTH_TO_SEASON = {
    "january": "Winter", "february": "Winter", "march": "Winter", "april": "Winter",
    "may": "Summer", "june": "Summer", "july": "Summer", "august": "Summer",
    "september": "Fall", "october": "Fall", "november": "Fall", "december": "Fall",
}

# "Winter 2027", "summer of 2027", and "Winter/January 2027" (Internship List's style).
_SEASON_RE = re.compile(r"\b(winter|spring|summer|fall)\b(?:\s*/\s*[a-z]+)?\s+(?:of\s+)?(20\d{2})\b", re.IGNORECASE)
# "January 2027", "(May 2027)"
_MONTH_RE = re.compile(r"\b(" + "|".join(_MONTH_TO_SEASON) + r")\s+(?:of\s+)?(20\d{2})\b", re.IGNORECASE)
# Descriptions often say "graduating in December 2027 or spring/summer 2028" or "complete a
# Bachelor's degree in CS ... between Spring/Summer/Fall 2028". Those are graduation dates,
# not the internship term, so skip a date that shares its sentence with "graduat..." or "degree".
_GRADUATION_RE = re.compile(r"\b(graduat\w*|degree)\b", re.IGNORECASE)
_SENTENCE_BREAK_RE = re.compile(r"[.!?\n]")


def _is_graduation_date(text: str, start: int) -> bool:
    """Look back up to 300 characters, but only within the current sentence."""
    window = text[max(0, start - 300):start]
    sentence = _SENTENCE_BREAK_RE.split(window)[-1]
    return bool(_GRADUATION_RE.search(sentence))


def _term_in(text: str) -> str | None:
    """Earliest season/month + year in the text that isn't part of a graduation date."""
    candidates = []
    for m in _SEASON_RE.finditer(text):
        candidates.append((m.start(), f"{m.group(1).capitalize()} {m.group(2)}"))
    for m in _MONTH_RE.finditer(text):
        candidates.append((m.start(), f"{_MONTH_TO_SEASON[m.group(1).lower()]} {m.group(2)}"))
    for start, term in sorted(candidates):  # sorted by position in the text
        if not _is_graduation_date(text, start):
            return term
    return None


def detect_term(title: str, description: str | None = None) -> str:
    """Return e.g. "Winter 2027". The title is checked first because it is the
    most reliable; the description is only a fallback. "Unknown" if neither says."""
    return _term_in(title) or (description and _term_in(description)) or "Unknown"


def is_remote(location: str | None, workplace_type: str | None = None) -> bool:
    """Prefer the board's structured workplace type; otherwise look for "remote" in the location text."""
    if workplace_type:
        return workplace_type.strip().lower() == "remote"
    return bool(location and "remote" in location.lower())
