import re

import pytest

from app.scoring import Skill, SkillConfig, coop_required, in_target_area, load_skills, score


def skill(name, weight, *patterns):
    return Skill(name, weight, tuple(re.compile(p, re.IGNORECASE) for p in patterns))


# A small, fixed config, so these tests don't break when skills.yaml is edited.
# full_match_weight=10 makes the score equal the matched weight, which keeps the maths obvious.
SKILLS = SkillConfig(
    skills=(
        skill("React", 3, r"\breact\b"),
        skill("Python", 2, r"\bpython\b"),
        skill("SQL", 2, r"\bsql\b", r"\bpostgres(ql)?\b"),
        skill("Java", 2, r"\bjava\b"),
        skill("Docker", 1, r"\bdocker\b"),
    ),
    full_match_weight=10,
)


def test_score_sums_matched_weights():
    assert score("Software Intern", "We use React and PostgreSQL.", SKILLS) == (5, ["React", "SQL"])


def test_each_skill_counts_once():
    assert score("Python Intern", "Python, Python and more Python.", SKILLS) == (2, ["Python"])


def test_java_does_not_match_javascript():
    assert score("Intern", "Experience with JavaScript", SKILLS) == (0, [])


def test_matches_title_and_handles_missing_description():
    assert score("Docker Platform Intern", None, SKILLS) == (1, ["Docker"])


def test_score_reaches_10_at_full_match_weight_and_is_capped():
    config = SkillConfig(SKILLS.skills, full_match_weight=4)
    assert score("Intern", "python and sql", config)[0] == 10          # 4 / 4
    assert score("Intern", "react python sql java", config)[0] == 10   # 9 / 4, capped
    assert score("Intern", "docker", config)[0] == 2                   # 1 / 4 = 2.5 -> 2


def test_real_skills_file_loads():
    config = load_skills()
    assert {"React", "Python", "SQL"} <= {s.name for s in config.skills}
    assert all(s.weight > 0 for s in config.skills)
    assert config.full_match_weight > 0


@pytest.mark.parametrize("text", [
    "Co-ops are only available to students enrolled in a co-op program.",           # Databricks
    "You must have a university that supports the co-op experience.",              # Samsara
    "Candidates must be currently enrolled in a recognized Co-op program.",
])
def test_coop_required_true(text):
    assert coop_required(text)


@pytest.mark.parametrize("text", [
    "Intent to return to the degree program after the completion of the internship/co-op",  # Stripe
    "has previous internship and/or co-op experience",                                       # Samsara
    "Summer 16-week co-op, or Summer 12-week internship",                                    # Databricks
    None,
])
def test_coop_required_false(text):
    assert not coop_required(text)


@pytest.mark.parametrize("location, remote, expected", [
    ("Toronto", False, True),
    ("Toronto, Ontario; Ottawa, Ontario; Greater Toronto Area", False, True),
    ("Oakville, Ontario - Canada", False, True),
    ("Waterloo, ON", False, True),
    ("Canada; Europe; United States", False, True),        # Cohere: "Canada" as its own location
    ("Remote - Canada", True, True),
    ("Vancouver, Canada", True, True),                     # remote job based in Canada
    ("Vancouver, Canada", False, False),                   # on-site in BC: outside my area
    ("London", False, False),                              # London, UK in this data
    ("San Francisco; Seattle", False, False),
    ("Remote - West Coast", True, False),
    (None, True, False),
])
def test_in_target_area(location, remote, expected):
    assert in_target_area(location, remote) is expected
