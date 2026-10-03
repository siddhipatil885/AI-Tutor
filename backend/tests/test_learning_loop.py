from app.services.diagnosis import diagnose


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
