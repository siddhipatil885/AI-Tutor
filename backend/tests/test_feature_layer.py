from app.services.assessment import create_assignment, generate_assessment
from app.services.auth import authenticate_user, require_role
from app.services.projects import recommend_projects
from app.services.teacher import build_teacher_dashboard, create_class, enroll_student, list_student_assignments


def test_generate_assessment_returns_question_metadata():
    assessment = generate_assessment(
        language="python",
        topics=["loop boundaries", "conditionals"],
        difficulty="beginner",
        question_count=3,
        question_types=["mcq", "output_prediction"],
    )

    assert assessment["language"] == "python"
    assert len(assessment["questions"]) == 3
    assert all(question["topic"] in {"loop boundaries", "conditionals"} for question in assessment["questions"])
    assert all(question["difficulty"] == "beginner" for question in assessment["questions"])
    assert all("misconception_ids" in question for question in assessment["questions"])


def test_teacher_dashboard_summarises_class_health():
    dashboard = build_teacher_dashboard(
        students=[
            {"name": "Asha", "mastery": {"C001": 0.82}, "active_misconceptions": ["M001"]},
            {"name": "Nikhil", "mastery": {"C001": 0.38}, "active_misconceptions": ["M001", "M002"]},
            {"name": "Sara", "mastery": {"C001": 0.91}, "active_misconceptions": []},
        ]
    )

    assert dashboard["total_students"] == 3
    assert dashboard["average_mastery"] > 0.5
    assert any(alert["student"] == "Nikhil" for alert in dashboard["at_risk_students"])
    assert dashboard["weak_topics"][0]["topic"] == "loop boundaries"


def test_recommend_projects_prioritises_gap_filling():
    recommended = recommend_projects(
        language="python",
        mastery={"C001": 0.32},
        completed_projects=[],
    )

    assert recommended[0]["language"] == "python"
    assert recommended[0]["title"]
    assert recommended[0]["focus"][0] == "C001"


def test_teacher_class_and_enrollment_are_persisted():
    teacher = create_class(teacher_id=1, name="Python Bootcamp", language="python", description="Starter cohort")
    enrollment = enroll_student(class_id=teacher["id"], student_id=2)

    assert teacher["name"] == "Python Bootcamp"
    assert teacher["teacher_id"] == 1
    assert enrollment["status"] == "active"
    assert enrollment["student_id"] == 2


def test_assignment_creation_persists_question_metadata():
    assignment = create_assignment(
        teacher_id=1,
        class_id=1,
        title="Loop Practice",
        language="python",
        difficulty="beginner",
        question_count=2,
        question_types=["mcq", "output_prediction"],
    )

    assert assignment["title"] == "Loop Practice"
    assert len(assignment["questions"]) == 2
    assert assignment["questions"][0]["language"] == "python"


def test_student_assignment_index_returns_enrolled_class_work():
    teacher_class = create_class(teacher_id=1, name="Student Cohort", language="python", description="For learner tasks")
    enroll_student(class_id=teacher_class["id"], student_id=99)
    assignment = create_assignment(
        teacher_id=1,
        class_id=teacher_class["id"],
        title="Student checkpoint",
        language="python",
        difficulty="beginner",
        question_count=2,
        question_types=["mcq", "output_prediction"],
    )

    student_assignments = list_student_assignments(student_id=99)

    assert any(item["id"] == assignment["id"] for item in student_assignments)
    assert any(item["class_name"] == "Student Cohort" for item in student_assignments)
    assert any(item["title"] == "Student checkpoint" for item in student_assignments)


def test_authenticate_user_assigns_teacher_role_for_teacher_credentials():
    user = authenticate_user("teacher@demo.com", "teacher123", "Teacher Demo")

    assert user["email"] == "teacher@demo.com"
    assert user["role"] == "teacher"


def test_require_role_rejects_student_access_to_teacher_only_route():
    try:
        require_role(["teacher"], {"id": 99, "role": "student"})
    except PermissionError:
        return

    raise AssertionError("student access should have been rejected")
