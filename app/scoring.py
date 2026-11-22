"""Fit scoring: how well a posting matches my skills, plus two flags I care about.

Kept simple on purpose, so every number can be explained:
  fit_score = min(10, round(10 * matched_weight / full_match_weight))
where matched_weight is the sum of the weights of the skills a posting mentions, and
full_match_weight (in skills.yaml) is how much counts as a perfect match.
"""
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

SKILLS_FILE = Path(__file__).resolve().parent.parent / "skills.yaml"


@dataclass(frozen=True)
class Skill:
    name: str
    weight: int
    patterns: tuple[re.Pattern, ...]


@dataclass(frozen=True)
class SkillConfig:
    skills: tuple[Skill, ...]
    full_match_weight: int


@lru_cache  # read and compile skills.yaml once per process, not once per posting
def load_skills(path: Path = SKILLS_FILE) -> SkillConfig:
    data = yaml.safe_load(path.read_text())
    skills = tuple(
        Skill(s["name"], int(s["weight"]), tuple(re.compile(p, re.IGNORECASE) for p in s["patterns"]))
        for s in data["skills"]
    )
    return SkillConfig(skills, int(data["full_match_weight"]))


def score(title: str, description: str | None, config: SkillConfig | None = None) -> tuple[int, list[str]]:
    """Return (fit_score 0-10, names of matched skills). Each skill counts once,
    however many times it is mentioned, so long descriptions don't win by repetition."""
    config = load_skills() if config is None else config
    text = f"{title}\n{description or ''}"
    matched = [s for s in config.skills if any(p.search(text) for p in s.patterns)]
    matched_weight = sum(s.weight for s in matched)
    fit = min(10, round(10 * matched_weight / config.full_match_weight))
    return fit, [s.name for s in matched]


# Wording seen in real postings (Stage 3 research):
#   "Co-ops are only available to students enrolled in a co-op program"   (Databricks)
#   "have a university that supports the co-op experience"                (Samsara)
# Not matched on purpose: "internship/co-op", "previous co-op experience", "16-week co-op".
_COOP_REQUIRED_RE = re.compile(
    r"enrolled in (?:a|an|your)\s+(?:[\w-]+\s+){0,3}co-?op\b"
    r"|(?:university|school|institution) that (?:supports|allows|offers) (?:a |the )?co-?op",
    re.IGNORECASE,
)


def coop_required(description: str | None) -> bool:
    """True if the posting says you must be in a co-op program. I'm not, so these get flagged."""
    return bool(description and _COOP_REQUIRED_RE.search(description))


# Target area: Ontario (GTA, Hamilton/Niagara, Kitchener-Waterloo, Ottawa) or remote in Canada.
# "London" is left out on purpose: in this data it is almost always London, UK.
_ONTARIO_RE = re.compile(
    r"\b(ontario|toronto|ottawa|waterloo|kitchener|cambridge, on|hamilton|niagara|st\.? catharines"
    r"|mississauga|oakville|burlington|markham|brampton|vaughan|richmond hill|guelph|gta"
    r"|greater toronto)\b|,\s*on\b",
    re.IGNORECASE,
)


def in_target_area(location: str | None, remote: bool) -> bool:
    """Look at each location (Ashby joins several with "; ") separately."""
    if not location:
        return False
    for part in re.split(r"[;|]", location):
        part = part.strip()
        if _ONTARIO_RE.search(part):
            return True
        # "Canada" on its own, "Remote - Canada", or any Canadian location on a remote job
        if re.fullmatch(r"(remote\s*[-–(]?\s*)?canada\)?", part, re.IGNORECASE):
            return True
        if remote and re.search(r"\bcanada\b", part, re.IGNORECASE):
            return True
    return False
