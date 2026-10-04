from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import Base, get_db
from app.main import app
from app.services import auth as auth_service


@pytest.fixture
def auth_client(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    settings = SimpleNamespace(
        neon_auth_issuer="https://auth.example.test",
        neon_auth_jwks_url="https://auth.example.test/.well-known/jwks.json",
        neon_auth_audience="authenticated",
        neon_auth_teacher_emails="teacher@example.test",
        neon_auth_admin_emails="admin@example.test",
    )

    class TestJwksClient:
        def get_signing_key_from_jwt(self, token):
            return SimpleNamespace(key=public_key)

    monkeypatch.setattr(auth_service, "get_settings", lambda: settings)
    monkeypatch.setattr(auth_service, "_jwks_client", lambda _url: TestJwksClient())

    def override_get_db():
        session = testing_session()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client, private_key
    app.dependency_overrides.pop(get_db, None)
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def token_for(private_key, subject: str, email: str, email_verified: bool = True) -> str:
    now = datetime.now(timezone.utc)
    claims = {
        "iss": "https://auth.example.test",
        "aud": "authenticated",
        "sub": subject,
        "email": email,
        "email_verified": email_verified,
        "name": email.split("@", 1)[0],
        "iat": now,
        "exp": now + timedelta(minutes=5),
    }
    return jwt.encode(claims, private_key, algorithm="RS256", headers={"kid": "test-key"})


def test_missing_bearer_token_ignores_forged_role_headers(auth_client):
    client, _private_key = auth_client

    response = client.get("/api/auth/me", headers={"X-User-Id": "1", "X-User-Role": "teacher"})

    assert response.status_code == 401


def test_invalid_bearer_token_is_rejected(auth_client):
    client, _private_key = auth_client

    response = client.get("/api/auth/me", headers={"Authorization": "Bearer not.a.jwt"})

    assert response.status_code == 401


def test_neon_auth_missing_configuration_fails_closed(auth_client, monkeypatch):
    client, _private_key = auth_client
    monkeypatch.setattr(auth_service, "get_settings", lambda: SimpleNamespace(
        neon_auth_issuer="",
        neon_auth_jwks_url="",
        neon_auth_audience="authenticated",
        neon_auth_teacher_emails="",
        neon_auth_admin_emails="",
    ))

    response = client.get("/api/auth/me", headers={"Authorization": "Bearer any-token"})

    assert response.status_code == 503


def test_verified_student_cannot_access_teacher_dashboard(auth_client):
    client, private_key = auth_client
    token = token_for(private_key, "student-subject", "learner@example.test")

    session = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    dashboard = client.get("/api/teacher/dashboard", headers={"Authorization": f"Bearer {token}"})

    assert session.status_code == 200
    assert session.json()["role"] == "student"
    assert dashboard.status_code == 403


def test_verified_allowlisted_teacher_receives_teacher_role(auth_client):
    client, private_key = auth_client
    token = token_for(private_key, "teacher-subject", "teacher@example.test")

    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()["role"] == "teacher"
    assert isinstance(response.json()["id"], int)


def test_user_id_in_path_cannot_access_another_learner(auth_client):
    client, private_key = auth_client
    token = token_for(private_key, "student-subject", "learner@example.test")

    response = client.get("/api/learner/999999/progress", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 403


def test_published_assignment_supports_multiple_student_attempts(auth_client):
    client, private_key = auth_client
    teacher_token = token_for(private_key, "teacher-subject", "teacher@example.test")
    student_token = token_for(private_key, "student-subject", "learner@example.test")
    other_teacher_token = token_for(private_key, "other-teacher-subject", "other-teacher@example.test")
    teacher_headers = {"Authorization": f"Bearer {teacher_token}"}
    student_headers = {"Authorization": f"Bearer {student_token}"}
    other_teacher_headers = {"Authorization": f"Bearer {other_teacher_token}"}

    student = client.get("/api/auth/me", headers=student_headers).json()
    class_response = client.post("/api/teacher/classes", headers=teacher_headers, json={
        "teacher_id": 999999,
        "name": "Assignment lifecycle cohort",
        "language": "python",
    })
    assert class_response.status_code == 201
    class_id = class_response.json()["id"]
    assert class_response.json()["teacher_id"] != 999999

    enroll_response = client.post(
        f"/api/teacher/classes/{class_id}/enroll?student_id={student['id']}",
        headers=teacher_headers,
    )
    assert enroll_response.status_code == 201

    assignment_response = client.post(
        "/api/teacher/assessments",
        headers=teacher_headers,
        params={
            "class_id": class_id,
            "teacher_id": 999999,
            "title": "Published checkpoint",
            "question_count": 2,
        },
    )
    assert assignment_response.status_code == 201
    assignment_id = assignment_response.json()["id"]
    assert assignment_response.json()["teacher_id"] != 999999
    assert client.get(f"/api/students/{student['id']}/assignments", headers=student_headers).json() == []

    denied_publish = client.post(f"/api/teacher/assignments/{assignment_id}/publish", headers=other_teacher_headers)
    assert denied_publish.status_code == 403

    published = client.post(f"/api/teacher/assignments/{assignment_id}/publish", headers=teacher_headers)
    assert published.status_code == 200
    assert published.json()["status"] == "published"

    visible = client.get(f"/api/students/{student['id']}/assignments", headers=student_headers)
    assert visible.status_code == 200
    assert len(visible.json()) == 1
    assert all("correct_answer" not in question for question in visible.json()[0]["questions"])
    answers = {str(question["id"]): question["correct_answer"] for question in assignment_response.json()["questions"]}

    first_attempt = client.post(f"/api/assignments/{assignment_id}/submissions", headers=student_headers, json={"answers": answers})
    second_answers = {question_id: "incorrect response" for question_id in answers}
    second_attempt = client.post(f"/api/assignments/{assignment_id}/submissions", headers=student_headers, json={"answers": second_answers})
    assert first_attempt.status_code == 201
    assert second_attempt.status_code == 201
    assert first_attempt.json()["attempt_number"] == 1
    assert first_attempt.json()["score"] == 100
    assert all(item["is_correct"] for item in first_attempt.json()["feedback"])
    assert second_attempt.json()["attempt_number"] == 2
    assert second_attempt.json()["score"] == 0

    history = client.get(f"/api/students/{student['id']}/assignments/{assignment_id}/attempts", headers=student_headers)
    review = client.get(f"/api/teacher/assignments/{assignment_id}/submissions", headers=teacher_headers)
    assert history.status_code == 200
    assert len(history.json()) == 2
    assert review.status_code == 200
    assert len(review.json()) == 2
    assert review.json()[0]["student_name"] == "learner"


def test_institution_membership_class_enrollment_and_reports(auth_client):
    client, private_key = auth_client
    admin_token = token_for(private_key, "admin-subject", "admin@example.test")
    teacher_token = token_for(private_key, "teacher-subject", "teacher@example.test")
    student_token = token_for(private_key, "student-subject", "learner@example.test")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    teacher_headers = {"Authorization": f"Bearer {teacher_token}"}
    student_headers = {"Authorization": f"Bearer {student_token}"}
    admin = client.get("/api/auth/me", headers=admin_headers).json()
    teacher = client.get("/api/auth/me", headers=teacher_headers).json()
    student = client.get("/api/auth/me", headers=student_headers).json()

    created = client.post("/api/institutions", headers=admin_headers, json={"name": "Verified Institution"})
    assert created.status_code == 201
    institution_id = created.json()["id"]
    assert created.json()["member_count"] == 1

    for email, role in [(teacher["email"], "teacher"), (student["email"], "student")]:
        response = client.post(
            f"/api/institutions/{institution_id}/members",
            headers=admin_headers,
            json={"email": email, "role": role},
        )
        assert response.status_code == 201

    teacher_class = client.post("/api/teacher/classes", headers=teacher_headers, json={
        "teacher_id": 999999,
        "name": "Institution cohort",
        "language": "python",
    })
    assert teacher_class.status_code == 201
    class_id = teacher_class.json()["id"]
    link = client.post(f"/api/institutions/{institution_id}/classes/{class_id}", headers=teacher_headers)
    assert link.status_code == 201

    enrollment = client.post(
        f"/api/institutions/{institution_id}/classes/{class_id}/enrollments?student_id={student['id']}",
        headers=teacher_headers,
    )
    assert enrollment.status_code == 201
    dashboard = client.get("/api/teacher/dashboard", headers=teacher_headers)
    assert dashboard.status_code == 200
    assert dashboard.json()["total_students"] == 1
    assert dashboard.json()["average_mastery"] is None
    assert dashboard.json()["average_assessment_performance"] is None
    assert dashboard.json()["weak_topics"] == []
    assert dashboard.json()["assignment_completion_rates"] == {}
    members = client.get(f"/api/institutions/{institution_id}/members", headers=admin_headers)
    assert members.status_code == 200
    assert {member["role"] for member in members.json()} == {"admin", "teacher", "student"}

    report = client.get(f"/api/institutions/{institution_id}/reports", headers=admin_headers)
    assert report.status_code == 200
    assert report.json()["member_count"] == 3
    assert report.json()["teacher_count"] == 1
    assert report.json()["student_count"] == 1
    assert report.json()["class_count"] == 1
    assert report.json()["attempt_count"] == 0
    assert report.json()["average_score"] is None

    student_report = client.get(f"/api/institutions/{institution_id}/reports", headers=student_headers)
    assert student_report.status_code == 403
    remove_teacher = client.delete(f"/api/institutions/{institution_id}/members/{teacher['id']}", headers=admin_headers)
    assert remove_teacher.status_code == 409
    remove_student = client.delete(f"/api/institutions/{institution_id}/members/{student['id']}", headers=admin_headers)
    assert remove_student.status_code == 204
    assert client.get(f"/api/students/{student['id']}/assignments", headers=student_headers).json() == []
    denied_class = client.get(f"/api/classes/{class_id}/assignments", headers=student_headers)
    assert denied_class.status_code == 403
    unlink = client.delete(f"/api/institutions/{institution_id}/classes/{class_id}", headers=admin_headers)
    assert unlink.status_code == 204
    remove_teacher = client.delete(f"/api/institutions/{institution_id}/members/{teacher['id']}", headers=admin_headers)
    assert remove_teacher.status_code == 204
    assert admin["role"] == "admin"