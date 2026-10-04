import { makeIntervention, submitAnswer } from './api'
import type { Diagnosis, Intervention } from '../types'

export type TaskEvidence = { taskId: string; conceptId?: string; output: string; userId: number; questionId: number }
export interface DiagnosisAdapter { diagnose(evidence: TaskEvidence): Promise<{ diagnosis: Diagnosis; submissionId: number }> }
export interface InterventionAdapter { create(submissionId: number): Promise<Intervention> }
export interface RecommendationAdapter { nextTask(input: { taskId: string; passed: boolean; conceptId?: string }): Promise<string | null> }
export interface LearningResourceAdapter { getResource(input: { conceptId: string; level: number }): Promise<null> }

/** Routes the initial loop-boundary task through the existing inspectable backend learning loop. */
export const existingDiagnosisAdapter: DiagnosisAdapter = {
  async diagnose(evidence) {
    const submission = await submitAnswer(evidence.questionId, evidence.output)
    return { diagnosis: submission.diagnosis, submissionId: submission.id }
  },
}
export const existingInterventionAdapter: InterventionAdapter = { create: makeIntervention }

/** Extension seams only: no ML model or RAG retrieval is invoked at this checkpoint. */
export const recommendationAdapter: RecommendationAdapter = { async nextTask() { return null } }
export const learningResourceAdapter: LearningResourceAdapter = { async getResource() { return null } }
