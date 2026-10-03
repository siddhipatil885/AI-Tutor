const base = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

async function get<T>(path: string): Promise<T> {
  const response = await fetch(`${base}${path}`)
  if (!response.ok) {
    throw new Error((await response.json().catch(() => null))?.detail || 'Backend request failed')
  }
  return response.json()
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${base}${path}`, {
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
export const getTeacherDashboard = () => get<{ total_students: number; average_mastery: number; weak_topics: Array<{ topic: string; mastery: number; weak_students: string[] }>; at_risk_students: Array<{ student: string; risk_score: number; reasons: string[] }> }>('/teacher/dashboard')
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
  return fetch(`${base}/teacher/assessments?${params.toString()}`, { method: 'POST' }).then(async (response) => {
    if (!response.ok) {
      throw new Error((await response.json().catch(() => null))?.detail || 'Backend request failed')
    }
    return response.json()
  })
}
export const getClassAssignments = (classId: number) => get<Array<{ id: number; class_id: number; teacher_id: number; title: string; language: string; difficulty: string; question_count: number; question_types: string[]; questions: Array<Record<string, unknown>>; status: string }>>(`/classes/${classId}/assignments`)
export const getStudentAssignments = (studentId: number) => get<Array<{ id: number; class_id: number; class_name: string; teacher_id: number; title: string; language: string; difficulty: string; question_count: number; question_types: string[]; questions: Array<Record<string, unknown>>; status: string }>>(`/students/${studentId}/assignments`)
export const generateAssessment = (payload: {
  language: string
  topics: string[]
  difficulty: string
  question_count: number
  question_types: string[]
}) => post<{ language: string; difficulty: string; questions: Array<{ id: number; topic: string; question_type: string; prompt: string; correct_answer: string; explanation: string; misconception_ids: string[] }> }>('/teacher/assessments/generate', payload)
export const getProjectCatalog = (language = 'python') => get<{ language: string; projects: Array<{ title: string; difficulty: string; description: string; focus: string[]; fit_score: number }> }>(`/projects?language=${encodeURIComponent(language)}`)
export const getProjectRecommendations = (payload: { language: string; mastery: Record<string, number>; completed_projects?: string[] }) => post<Array<{ title: string; language: string; difficulty: string; description: string; focus: string[]; fit_score: number }>>('/projects/recommend', payload)
