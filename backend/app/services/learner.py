from sqlalchemy.orm import Session
from app.models.entities import LearnerProfile


def profile_for(db: Session, user_id: int) -> LearnerProfile:
    profile = db.query(LearnerProfile).filter_by(user_id=user_id).first()
    if not profile:
        profile = LearnerProfile(user_id=user_id, mastery={"C001": 0.35}, active_misconceptions=[], resolved_misconceptions=[], trajectory=[])
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


def record_concept_success(db: Session, profile: LearnerProfile, concept_id: str, evidence: list[str]) -> None:
    mastery = dict(profile.mastery or {})
    trajectory = list(profile.trajectory or [])
    already_recorded = any(
        item.get("status") == "demonstrated" and item.get("misconception_id") == concept_id
        for item in trajectory
    )
    if not already_recorded:
        mastery[concept_id] = min(1.0, round(mastery.get(concept_id, 0.35) + 0.15, 2))
        trajectory.append({"status": "demonstrated", "misconception_id": concept_id, "evidence": evidence})
        profile.mastery, profile.trajectory = mastery, trajectory[-10:]
        db.commit()


def apply_assessment(db: Session, profile: LearnerProfile, misconception_id: str, correct: bool, evidence: list[str]) -> str:
    active, resolved, mastery, trajectory = list(profile.active_misconceptions or []), list(profile.resolved_misconceptions or []), dict(profile.mastery or {}), list(profile.trajectory or [])
    if correct:
        status = "resolved"
        if misconception_id in active: active.remove(misconception_id)
        if misconception_id not in resolved: resolved.append(misconception_id)
        mastery["C001"] = min(1.0, round(mastery.get("C001", .35) + .35, 2))
    else:
        status = "unresolved"
        if misconception_id not in active: active.append(misconception_id)
        mastery["C001"] = max(0.0, round(mastery.get("C001", .35) - .08, 2))
    trajectory.append({"status": status, "misconception_id": misconception_id, "evidence": evidence})
    profile.active_misconceptions, profile.resolved_misconceptions = active, resolved
    profile.mastery, profile.trajectory = mastery, trajectory[-10:]
    db.commit()
    return status
