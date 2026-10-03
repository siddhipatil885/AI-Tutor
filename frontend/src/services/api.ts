import type { Assessment, Diagnosis, Intervention, JudgeResult, Learner, Question } from '../types'

const fallbackApiBase = typeof window === 'undefined'
  ? 'http://localhost:8000/api'
  : `${window.location.protocol}//${window.location.hostname}:8000/api`

const base = import.meta.env.VITE_API_URL || fallbackApiBase
async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${base}${path}`, { headers: {'Content-Type': 'application/json'}, ...init })
  if (!response.ok) throw new Error((await response.json().catch(() => null))?.detail || 'Something went wrong')
  return response.json()
}
export const getQuestion = () => api<Question>('/questions/default')
export const getLearner = () => api<Learner>('/learner/1')
export const submitAnswer = (question_id: number, answer: string, reasoning?: string) => api<{id: number; diagnosis: Diagnosis}>('/submissions', {method:'POST', body:JSON.stringify({user_id:1, question_id, answer, reasoning})})
export const makeIntervention = (submissionId: number) => api<Intervention>(`/interventions?submission_id=${submissionId}`, {method:'POST'})
export const startReassessment = (intervention_id: number) => api<Assessment>('/reassessment', {method:'POST', body:JSON.stringify({user_id:1, intervention_id})})
export const answerReassessment = (intervention_id: number, assessment_id: number, answer: string) => api<Assessment>('/reassessment', {method:'POST', body:JSON.stringify({user_id:1, intervention_id, assessment_id, answer})})
export const judgePythonSubmission = (payload: { problem_id: string; language?: string; function_name: string; code: string; tests: unknown[] }) => api<JudgeResult>('/judge/python', { method: 'POST', body: JSON.stringify({ ...payload, language: payload.language ?? 'python' }) })
