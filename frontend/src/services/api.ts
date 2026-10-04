const base = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'
import { getAccessToken } from './auth'
import type { Diagnosis, Intervention } from '../types'

type CodeDiagnosisResult = {
  predicted_misconception: { id: string; name: string; description: string }
  confidence: number
  top_predictions: Array<{ misconception: string; confidence: number; description?: string }>
}

async function request(path: string, init: RequestInit = {}) {
  const headers = new Headers(init.headers)
  const token = await getAccessToken()
  if (token) headers.set('Authorization', `Bearer ${token}`)
  return fetch(`${base}${path}`, { ...init, headers })
}

async function get<T>(path: string): Promise<T> {
  const response = await request(path)
  if (!response.ok) {
    throw new Error((await response.json().catch(() => null))?.detail || 'Backend request failed')
  }
  return response.json()
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const response = await request(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!response.ok) {
    throw new Error((await response.json().catch(() => null))?.detail || 'Backend request failed')
  }
  return response.json()
}

export const getBackendHealth = () => get<{ status: string }>('/health')
export const getDatabaseHealth = () => get<{ status: string }>('/health/db')
export const getTeacherDashboard = () => get<{ total_students: number; active_students: number; average_assessment_performance: number | null; average_mastery: number | null; average_concept_mastery: number | null; assignment_completion_rates: Record<string, number>; weak_topics: Array<{ topic: string; mastery: number; weak_students: string[]; misconception_ids?: string[] }>; at_risk_students: Array<{ student: string; risk_score: number; reasons: string[] }> }>('/teacher/dashboard')
export const createClass = (payload: { teacher_id: number; name: string; language: string; description?: string }) => post<{ id: number; teacher_id: number; name: string; language: string; description?: string }>('/teacher/classes', payload)
export const listClasses = (teacherId: number) => get<Array<{ id: number; teacher_id: number; name: string; language: string; description?: string }>>(`/teacher/classes?teacher_id=${teacherId}`)
export const createAssignment = (payload: { class_id: number; teacher_id: number; title: string; language: string; difficulty: string; question_count: number; question_types?: string[] }) => {
  const params = new URLSearchParams({
    class_id: String(payload.class_id),
    teacher_id: String(payload.teacher_id),
    title: payload.title,
    language: payload.language,
    difficulty: payload.difficulty,
    question_count: String(payload.question_count),
  })
  if (payload.question_types?.length) {
    params.set('question_types', payload.question_types.join(','))
  }
  return request(`/teacher/assessments?${params.toString()}`, { method: 'POST' }).then(async (response) => {
    if (!response.ok) {
      throw new Error((await response.json().catch(() => null))?.detail || 'Backend request failed')
    }
    return response.json()
  })
}
export const createLab = (classId: number, payload: { teacher_id: number; title: string; language: string; concept: string; difficulty: string; instructions?: string; duration_minutes?: number }) => post<{ id: number; class_id: number; teacher_id: number; title: string; language: string; concept: string; difficulty: string; instructions?: string; duration_minutes: number; status: string }>(`/teacher/classes/${classId}/labs`, payload)
export const listLabs = (classId: number) => get<Array<{ id: number; class_id: number; teacher_id: number; title: string; language: string; concept: string; difficulty: string; instructions?: string; duration_minutes: number; status: string }>>(`/classes/${classId}/labs`)
export const updateLabStatus = (labId: number, status: string) => request(`/labs/${labId}/status?status=${encodeURIComponent(status)}`, { method: 'POST' }).then(async (response) => {
  if (!response.ok) {
    throw new Error((await response.json().catch(() => null))?.detail || 'Backend request failed')
  }
  return response.json()
})
export const getClassAssignments = (classId: number) => get<Array<{ id: number; class_id: number; teacher_id: number; title: string; language: string; difficulty: string; question_count: number; question_types: string[]; questions: Array<Record<string, unknown>>; status: string }>>(`/classes/${classId}/assignments`)
export type StudentAssignment = { id: number; class_id: number; class_name: string; teacher_id: number; title: string; language: string; difficulty: string; question_count: number; question_types: string[]; questions: Array<{ id: number; language: string; topic: string; question_type: string; difficulty: string; prompt: string }>; status: string }
export type AssignmentFeedback = { question_id: number; answer: string; correct_answer: string; is_correct: boolean; explanation: string }
export type AssignmentAttempt = { id: number; assignment_id: number; student_id: number; attempt_number: number; score: number; answers: Record<string, string>; feedback: AssignmentFeedback[]; created_at: string }
export type AssignmentReview = AssignmentAttempt & { student_name: string }
export const getStudentAssignments = (studentId: number) => get<StudentAssignment[]>(`/students/${studentId}/assignments`)
export const submitAssignment = (assignmentId: number, answers: Record<string, string>) => post<AssignmentAttempt>(`/assignments/${assignmentId}/submissions`, { answers })
export const getStudentAssignmentAttempts = (studentId: number, assignmentId: number) => get<AssignmentAttempt[]>(`/students/${studentId}/assignments/${assignmentId}/attempts`)
export const publishAssignment = (assignmentId: number) => post<{ id: number; status: string }>(`/teacher/assignments/${assignmentId}/publish`, {})
export const getAssignmentReviews = (assignmentId: number) => get<AssignmentReview[]>(`/teacher/assignments/${assignmentId}/submissions`)
export type InstitutionSummary = { id: number; name: string; role: string; member_count: number; created_at: string }
export type InstitutionMember = { user_id: number; name: string; email?: string; role: string; status: string }
export type InstitutionClass = { id: number; name: string; language: string; teacher_id: number }
export type InstitutionReport = { member_count: number; teacher_count: number; student_count: number; class_count: number; published_assignment_count: number; attempt_count: number; average_score: number | null }
export const getInstitutions = () => get<InstitutionSummary[]>('/institutions')
export const createInstitution = (name: string) => post<InstitutionSummary>('/institutions', { name })
export const getInstitutionMembers = (institutionId: number) => get<InstitutionMember[]>(`/institutions/${institutionId}/members`)
export const addInstitutionMember = (institutionId: number, payload: { email: string; role: 'admin' | 'teacher' | 'student' }) => post<InstitutionMember>(`/institutions/${institutionId}/members`, payload)
export const removeInstitutionMember = async (institutionId: number, userId: number) => {
  const response = await request(`/institutions/${institutionId}/members/${userId}`, { method: 'DELETE' })
  if (!response.ok) throw new Error((await response.json().catch(() => null))?.detail || 'Backend request failed')
}
export const getInstitutionClasses = (institutionId: number) => get<InstitutionClass[]>(`/institutions/${institutionId}/classes`)
export const linkInstitutionClass = (institutionId: number, classId: number) => post<InstitutionClass>(`/institutions/${institutionId}/classes/${classId}`, {})
export const unlinkInstitutionClass = async (institutionId: number, classId: number) => {
  const response = await request(`/institutions/${institutionId}/classes/${classId}`, { method: 'DELETE' })
  if (!response.ok) throw new Error((await response.json().catch(() => null))?.detail || 'Backend request failed')
}
export const enrollInstitutionStudent = (institutionId: number, classId: number, studentId: number) => post<{ id: number; class_id: number; student_id: number; status: string }>(`/institutions/${institutionId}/classes/${classId}/enrollments?student_id=${studentId}`, {})
export const getInstitutionReport = (institutionId: number) => get<InstitutionReport>(`/institutions/${institutionId}/reports`)
export const getStudentLabs = (studentId: number) => get<Array<{ id: number; class_id: number; class_name: string; teacher_id: number; title: string; language: string; concept: string; difficulty: string; instructions?: string; duration_minutes: number; status: string }>>(`/students/${studentId}/labs`)
export const submitLabProgress = (studentId: number, labId: number, payload: { answer: string; reflection?: string; status?: string }) => post<{ id: number; student_id: number; lab_id: number; answer: string; reflection?: string; status: string }>(`/students/${studentId}/labs/${labId}/submit`, payload)
export const generateAssessment = (payload: {
  language: string
  topics: string[]
  difficulty: string
  question_count: number
  question_types: string[]
}) => post<{ language: string; difficulty: string; questions: Array<{ id: number; topic: string; question_type: string; prompt: string; correct_answer: string; explanation: string; misconception_ids: string[] }> }>('/teacher/assessments/generate', payload)
export const getProjectCatalog = (language = 'python') => get<{ language: string; projects: Array<{ title: string; difficulty: string; description: string; focus: string[]; fit_score: number }> }>(`/projects?language=${encodeURIComponent(language)}`)
export const getProjectRecommendations = (payload: { language: string; mastery: Record<string, number>; completed_projects?: string[] }) => post<Array<{ title: string; language: string; difficulty: string; description: string; focus: string[]; fit_score: number }>>('/projects/recommend', payload)
export const submitAnswer = (question_id: number, answer: string, reasoning?: string) =>
  post<{ id: number; diagnosis: Diagnosis }>('/submissions', { user_id: 1, question_id, answer, reasoning })
export const makeIntervention = (submissionId: number) =>
  post<Intervention>(`/interventions?submission_id=${submissionId}`, {})
export const diagnoseCode = (payload: { problem_id: string; language: string; code: string }) =>
  post<CodeDiagnosisResult>('/diagnose/code', payload)
