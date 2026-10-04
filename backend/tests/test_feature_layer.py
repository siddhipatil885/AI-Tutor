from app.services.assessment import create_assignment, generate_assessment
from fastapi import HTTPException

from app.services.auth import require_role
from app.services.projects import recommend_projects
from app.services.teacher import build_teacher_dashboard, create_class, create_lab, enroll_student, list_labs, list_student_assignments, list_student_labs, submit_lab_progress, update_lab_status


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


def test_teacher_dashboard_does_not_invent_empty_metrics():
    dashboard = build_teacher_dashboard([])

    assert dashboard["total_students"] == 0
    assert dashboard["average_mastery"] is None
    assert dashboard["average_assessment_performance"] is None
    assert dashboard["weak_topics"] == []
    assert dashboard["assignment_completion_rates"] == {}


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


def test_lab_creation_and_listing_are_persisted_for_a_classroom():
    teacher_class = create_class(teacher_id=1, name="Lab Cohort", language="python", description="Loop practice cohort")
    lab = create_lab(
        teacher_id=1,
        class_id=teacher_class["id"],
        title="Python loops lab",
        language="python",
        concept="loop boundaries",
        difficulty="beginner",
        instructions="Practice range boundaries and iteration patterns.",
        duration_minutes=30,
    )

    labs = list_labs(class_id=teacher_class["id"])

    assert lab["title"] == "Python loops lab"
    assert lab["status"] == "draft"
    assert any(item["id"] == lab["id"] for item in labs)


def test_lab_status_can_transition_to_active_and_completed():
    teacher_class = create_class(teacher_id=1, name="Status Lab", language="python", description="Status lifecycle cohort")
    lab = create_lab(
        teacher_id=1,
        class_id=teacher_class["id"],
        title="Loop status lab",
        language="python",
        concept="loop boundaries",
        difficulty="beginner",
        instructions="Practice loop boundaries.",
        duration_minutes=25,
    )

    active = update_lab_status(lab_id=lab["id"], status="active")
    completed = update_lab_status(lab_id=lab["id"], status="completed")

    assert active["status"] == "active"
    assert completed["status"] == "completed"


def test_student_lab_index_and_submission_are_persisted():
    teacher_class = create_class(teacher_id=1, name="Active Lab Cohort", language="python", description="Student lab cohort")
    enroll_student(class_id=teacher_class["id"], student_id=101)
    lab = create_lab(
        teacher_id=1,
        class_id=teacher_class["id"],
        title="Active loop lab",
        language="python",
        concept="loop boundaries",
        difficulty="beginner",
        instructions="Work through the boundary pattern and explain your answer.",
        duration_minutes=35,
        status="active",
    )

    submission = submit_lab_progress(
        lab_id=lab["id"],
        student_id=101,
        answer="I checked the stopping value and kept the loop inside the boundary.",
        reflection="The key idea was excluding the final value while still counting the start.",
    )
    labs_for_student = list_student_labs(student_id=101)

    assert submission["lab_id"] == lab["id"]
    assert submission["status"] == "submitted"
    assert any(item["id"] == lab["id"] for item in labs_for_student)


def test_require_role_rejects_student_access_to_teacher_only_route():
    try:
        require_role(["teacher"], {"id": 99, "role": "student"})
    except HTTPException as error:
        assert error.status_code == 403
    else:
        raise AssertionError("student access should have been rejected")
