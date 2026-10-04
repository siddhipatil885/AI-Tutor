from types import SimpleNamespace

from app.services.diagnosis import diagnose
from app.services.learner import record_concept_success


def test_diagnoses_off_by_one_from_extra_value():
    result = diagnose("1 2 3", "1 2 3 4")
    assert result.misconception_id == "M001"
    assert result.needs_intervention is True
    assert result.error_type == "conceptual"


def test_keeps_unknown_wrong_answers_uncertain():
    result = diagnose("1 2 3", "banana")
    assert result.is_correct is False
    assert result.misconception_id is None
    assert result.error_type == "uncertain"


def test_marks_exact_match_correct():
    result = diagnose("1 2 3", " 1   2  3 ")
    assert result.is_correct is True
    assert result.needs_intervention is False


def test_concept_mastery_credit_is_recorded_once():
    class Session:
        commits = 0

        def commit(self):
            self.commits += 1

    session = Session()
    profile = SimpleNamespace(mastery={"C001": 0.35}, trajectory=[])
    evidence = ["The submitted answer matches the expected output."]

    record_concept_success(session, profile, "C001", evidence)
    record_concept_success(session, profile, "C001", evidence)

    assert profile.mastery["C001"] == 0.5
    assert len(profile.trajectory) == 1
    assert session.commits == 1
