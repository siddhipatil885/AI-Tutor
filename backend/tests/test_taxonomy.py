"""Contract tests for the data-first misconception taxonomy migration."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TAXONOMY_PATH = ROOT / "data" / "rag" / "taxonomy" / "relearn_taxonomy.json"
LEGACY_MAP_PATH = ROOT / "data" / "rag" / "taxonomy" / "legacy_id_map.json"

CANONICAL_IDS = {
    *(f"LOOP-{number:02d}" for number in range(1, 6)),
    *(f"ARR-{number:02d}" for number in range(6, 11)),
    *(f"COND-{number:02d}" for number in range(11, 16)),
    *(f"FUNC-{number:02d}" for number in range(16, 21)),
    *(f"REC-{number:02d}" for number in range(21, 26)),
}
REQUIRED_FIELDS = {
    "misconception_id", "name", "category", "concept", "short_definition",
    "detailed_explanation", "common_symptoms", "incorrect_reasoning_examples",
    "correct_reasoning", "common_student_language", "prerequisites", "difficulty",
    "intervention_goal", "distinguish_from", "error_type", "frequency_evidence",
    "evidence_basis", "evidence_source_ids", "evidence_notes", "diagnostic_signals",
    "counter_signals",
}
VALID_ERROR_TYPES = {"conceptual", "procedural", "reasoning", "control_flow", "boundary", "syntax", "semantic"}
VALID_FREQUENCY_EVIDENCE = {"high", "medium", "lower", "unknown"}
VALID_EVIDENCE_BASES = {"literature", "observed_student_data", "expert_taxonomy", "mixed"}


def load_taxonomy() -> dict:
    """Read and parse the repository's canonical misconception taxonomy."""
    return json.loads(TAXONOMY_PATH.read_text())


def test_taxonomy_has_exactly_the_25_canonical_ids():
    """Verify that all 25 canonical IDs occur exactly once."""
    records = load_taxonomy()["misconceptions"]
    assert len(records) == 25
    assert {record["misconception_id"] for record in records} == CANONICAL_IDS
    assert len({record["misconception_id"] for record in records}) == 25


def test_every_canonical_record_has_evidence_and_diagnostic_contract():
    """Check required fields, evidence references, and diagnostic signals."""
    taxonomy = load_taxonomy()
    source_ids = set(taxonomy["evidence_sources"])
    for record in taxonomy["misconceptions"]:
        assert REQUIRED_FIELDS <= set(record), record["misconception_id"]
        assert record["error_type"] in VALID_ERROR_TYPES
        assert record["frequency_evidence"] in VALID_FREQUENCY_EVIDENCE
        assert record["evidence_basis"] in VALID_EVIDENCE_BASES
        assert record["diagnostic_signals"], record["misconception_id"]
        assert record["counter_signals"], record["misconception_id"]
        assert record["distinguish_from"], record["misconception_id"]
        assert set(record["evidence_source_ids"]) <= source_ids
        assert record["evidence_notes"].strip()


def test_distinguishing_ids_are_canonical_and_not_self_references():
    """Ensure distinguishing references identify other canonical records."""
    for record in load_taxonomy()["misconceptions"]:
        related = set(record["distinguish_from"])
        assert related <= CANONICAL_IDS
        assert record["misconception_id"] not in related


def test_legacy_m_ids_map_one_to_one_to_all_canonical_ids():
    """Verify a one-to-one mapping from legacy IDs to all canonical IDs."""
    mapping = json.loads(LEGACY_MAP_PATH.read_text())["legacy_to_canonical"]
    expected_legacy_ids = {f"M{number:03d}" for number in range(1, 26)}
    assert set(mapping) == expected_legacy_ids
    assert set(mapping.values()) == CANONICAL_IDS
    assert len(set(mapping.values())) == 25


def test_taxonomy_does_not_claim_a_global_frequency_ranking():
    """Check that the selection statement disclaims a global top-25 ranking."""
    statement = load_taxonomy()["taxonomy"]["selection_statement"].lower()
    assert "not a statistically ranked global top-25 list" in statement
