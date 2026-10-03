from __future__ import annotations


PROJECT_CATALOG = {
    "python": [
        {
            "title": "Python Quiz Game",
            "difficulty": "beginner",
            "description": "Build a small interactive quiz that asks questions and tracks score.",
            "focus": ["C001", "C002"],
        },
        {
            "title": "Expense Tracker",
            "difficulty": "intermediate",
            "description": "Store expenses, categorize them, and summarize totals.",
            "focus": ["C004"],
        },
        {
            "title": "Number Guessing Game",
            "difficulty": "beginner",
            "description": "Create a loop-driven guessing game with hints and score tracking.",
            "focus": ["C001"],
        },
    ],
    "c": [
        {
            "title": "Student Record System",
            "difficulty": "intermediate",
            "description": "Use arrays and functions to manage student records.",
            "focus": ["C003", "C004"],
        },
        {
            "title": "Menu-Driven Calculator",
            "difficulty": "beginner",
            "description": "Build a calculator with different operations and validation.",
            "focus": ["C001", "C002"],
        },
    ],
    "html": [
        {
            "title": "Personal Portfolio",
            "difficulty": "beginner",
            "description": "Design a landing page with a biography, skills, and contact details.",
            "focus": ["C002"],
        },
        {
            "title": "Registration Form",
            "difficulty": "beginner",
            "description": "Create a styled form with validation and structure for inputs.",
            "focus": ["C002"],
        },
    ],
}


def recommend_projects(language: str, mastery: dict[str, float], completed_projects: list[str] | None = None) -> list[dict]:
    catalog = PROJECT_CATALOG.get((language or "python").lower(), PROJECT_CATALOG["python"])
    completed = set(completed_projects or [])
    recommendations = []

    for project in catalog:
        if project["title"] in completed:
            continue
        fit_score = 0.0
        for concept_id in project["focus"]:
            mastery_value = mastery.get(concept_id, 0.5)
            fit_score += max(0.0, 1.0 - mastery_value)
        fit_score += 0.25
        recommendations.append(
            {
                "title": project["title"],
                "language": (language or "python").lower(),
                "difficulty": project["difficulty"],
                "description": project["description"],
                "focus": project["focus"],
                "fit_score": round(max(0.0, min(1.0, fit_score / max(1, len(project["focus"])))), 3),
            }
        )

    recommendations.sort(key=lambda item: item["fit_score"], reverse=True)
    return recommendations[:3]
