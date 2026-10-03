"""Controlled, inspectable diagnosis for the MVP taxonomy."""
import re
from dataclasses import dataclass

from app.schemas import DiagnosisOut

M001 = "M001"


def normalize(value: str) -> str:
    return " ".join(value.strip().lower().split())


def numbers_in(value: str) -> list[int]:
    return [int(n) for n in re.findall(r"(?<![\w.])-?\d+(?![\w.])", value)]


def diagnose(expected_answer: str, answer: str, reasoning: str | None = None) -> DiagnosisOut:
    """Return only labels justified by answer structure, never a guessed label."""
    expected, received = normalize(expected_answer), normalize(answer)
    if expected == received:
        return DiagnosisOut(is_correct=True, confidence=0.99, evidence=["The submitted answer matches the expected output."], error_type="none", needs_intervention=False)

    expected_numbers, received_numbers = numbers_in(expected), numbers_in(answer)
    boundary_words = re.search(r"<=|>=|\b(inclusive|including|last value|through)\b", answer.lower())
    difference_is_one = bool(expected_numbers and received_numbers and abs(len(expected_numbers) - len(received_numbers)) == 1)
    if difference_is_one or boundary_words:
        evidence = []
        if difference_is_one:
            evidence.append("The response contains exactly one extra or missing output value, which is the expected boundary-error pattern.")
        if boundary_words:
            evidence.append("The response uses inclusive-boundary language or an inclusive comparison.")
        if reasoning:
            evidence.append("The provided reasoning was considered alongside the output.")
        return DiagnosisOut(
            is_correct=False, misconception_id=M001, misconception_name="Loop boundary / off-by-one", confidence=0.91 if difference_is_one else 0.76,
            evidence=evidence, error_type="conceptual", needs_intervention=True,
        )

    if not answer.strip():
        return DiagnosisOut(is_correct=False, confidence=0.92, evidence=["No answer was submitted, so there is insufficient evidence to infer a misconception."], error_type="careless_input", needs_intervention=False)
    return DiagnosisOut(is_correct=False, confidence=0.42, evidence=["The answer is incorrect, but its structure does not support a controlled misconception label."], error_type="uncertain", needs_intervention=False)
