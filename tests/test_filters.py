import pytest

from app.filters import detect_term, is_internship, is_remote


# parametrize runs the same test once per tuple; each shows up as its own result.
# Titles are real ones seen on the boards during Step 0.
@pytest.mark.parametrize("title", [
    "Software Engineering Intern (January 2027)",
    "Data Analyst, Intern",
    "Internship - Software Engineering",
    "Machine Learning Intern/Co-op  (Winter 2027)",
    "Co-op/Intern, Accounting - Winter 2027",
    "Student Developer",
])
def test_is_internship_true(title):
    assert is_internship(title)


@pytest.mark.parametrize("title", [
    "Senior / Principal Product Manager",
    "International Tax Manager",   # "intern" inside a longer word must not match
    "Internal Tools Engineer",
])
def test_is_internship_false(title):
    assert not is_internship(title)


def test_is_internship_uses_employment_type_when_title_is_vague():
    assert is_internship("Software Engineer, Summer", employment_type="Intern/Co-op")
    assert not is_internship("Software Engineer", employment_type="FullTime")


@pytest.mark.parametrize("title, expected", [
    ("Research Internship (Winter 2027)", "Winter 2027"),
    ("High School Internship, Software Engineering (Summer 2027)", "Summer 2027"),
    ("Marketing Intern, Latin America (Winter/January 2027, 12 Months)", "Winter 2027"),
    ("Software Engineering Intern (January 2027)", "Winter 2027"),
    ("Software Engineering Intern (May 2027)", "Summer 2027"),
    ("Data Analyst, Intern", "Unknown"),
])
def test_detect_term_from_title(title, expected):
    assert detect_term(title) == expected


def test_detect_term_falls_back_to_description():
    assert detect_term("Data Analyst, Intern", "This is a 4-month Summer 2027 placement.") == "Summer 2027"


def test_detect_term_prefers_title_over_description():
    assert detect_term("Intern (Winter 2027)", "Past interns joined in Summer 2026.") == "Winter 2027"


def test_is_remote():
    assert is_remote("Remote - Canada")
    assert not is_remote("Toronto")
    assert not is_remote(None)
    # Structured field wins over location text
    assert is_remote("Toronto", workplace_type="Remote")
    assert not is_remote("Remote friendly", workplace_type="Hybrid")


# Regression tests from real Stripe descriptions (Step 5): graduation dates are not terms.
def test_detect_term_ignores_graduation_dates():
    text = "with the expectation of graduating in December 2027 or spring/summer 2028. Experience with SQL"
    assert detect_term("Data Analyst, Intern", text) == "Unknown"


def test_detect_term_ignores_degree_completion_dates():
    # Real Samsara wording (Step 9)
    text = ("Complete a Bachelor's degree in Computer Science, Mathematics, Software Engineering, "
            "Physics, or Data Science between Spring/Summer/Fall 2028 or Winter 2029.")
    assert detect_term("Software Engineering Internship - San Francisco", text) == "Unknown"


def test_graduation_check_stays_within_one_sentence():
    text = "Applicants must be graduating soon. This internship runs Summer 2027."
    assert detect_term("Software Intern", text) == "Summer 2027"


def test_detect_term_handles_season_of_year_and_skips_later_graduation_date():
    text = ("We are excited to offer internships for the summer of 2027. Candidates should have "
            "the expectation of graduating in winter 2027 or spring/summer 2028.")
    assert detect_term("Master's Machine Learning Engineer, Intern", text) == "Summer 2027"
