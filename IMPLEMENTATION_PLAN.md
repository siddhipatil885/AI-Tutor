# ReLearn implementation plan

## Architecture summary

The codebase is a small adaptive-learning MVP built around a diagnosis loop:

- FastAPI backend with SQLAlchemy models
- Explainable diagnosis for a controlled misconception taxonomy
- Minimal learner profile tracking and reassessment flow
- Vite + React frontend with a dashboard-oriented shell

The current MVP is centered on Python loop-boundary diagnosis and can be extended without replacing the diagnosis model.

## Reusable modules

- `backend/app/services/diagnosis.py` for deterministic misconception detection
- `backend/app/services/learner.py` for learner-profile updates
- `backend/app/services/projects.py` for project fit scoring
- `backend/app/services/teacher.py` for class-level dashboard summaries
- `backend/app/services/assessment.py` for assessment generation metadata

## Schema and API changes

- Add lightweight classroom metadata and user role support for teacher workflows.
- Extend the API with teacher dashboard summary endpoints.
- Add assessment-generation endpoints that return question metadata and misconception tags.
- Add project recommendation endpoints that rank project fit based on concept mastery.
- Keep the existing diagnosis and learner update flow intact.

## Implementation phases

1. Stabilize the project foundation and test environment.
2. Add teacher-facing summary services and APIs.
3. Add assessment-generation and project-recommendation modules.
4. Connect the frontend to the new summary and generation endpoints.
5. Extend with richer DB-backed class management and role checks in later iterations.

## Risks and dependencies

- Real authentication and authorization are not yet implemented; the role structure is a clean integration boundary.
- Assessment generation is template-driven rather than a production LLM pipeline.
- Project recommendations are based on mastery heuristics rather than a trained ranking model.

## Current status

The foundation for teacher analytics, assessment generation, and project recommendations is implemented and validated with backend tests.
