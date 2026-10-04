import { makeIntervention, submitAnswer, diagnoseTutor } from './api'
import type { Diagnosis, Intervention } from '../types'

export type TaskEvidence = { taskId: string; conceptId?: string; output: string; code?: string; allPassed?: boolean; userId: number; questionId: number }
export interface DiagnosisAdapter { diagnose(evidence: TaskEvidence): Promise<{ diagnosis: Diagnosis; submissionId: number }> }
export interface InterventionAdapter { create(submissionId: number): Promise<Intervention> }
export interface RecommendationAdapter { nextTask(input: { taskId: string; passed: boolean; conceptId?: string }): Promise<string | null> }
export interface LearningResourceAdapter { getResource(input: { conceptId: string; level: number }): Promise<null> }

/** Routes the initial loop-boundary task through the existing inspectable backend learning loop. */
export const existingDiagnosisAdapter: DiagnosisAdapter = {
  async diagnose(evidence) {
    if (evidence.code) {
        const mlResult = await diagnoseTutor({ user_id: evidence.userId, question_id: evidence.questionId, problem_id: evidence.taskId, language: 'python', code: evidence.code })
        
        let evidenceStrings = [mlResult.predicted_misconception.description || mlResult.predicted_misconception.name]
        if (mlResult.gemini_hint) {
             evidenceStrings.unshift(`💡 Hint: ${mlResult.gemini_hint}`)
        }
        if (mlResult.top_predictions && mlResult.top_predictions.length > 1) {
             const alt = mlResult.top_predictions[1]
             evidenceStrings.push(`Alternative: ${alt.description || alt.misconception} (${Math.round(alt.confidence * 100)}%)`)
        }

        const diagnosis: Diagnosis = {
            id: Date.now(),
            is_correct: evidence.allPassed === true,
            misconception_id: mlResult.predicted_misconception.id,
            misconception_name: mlResult.predicted_misconception.name,
            confidence: mlResult.confidence,
            evidence: evidenceStrings,
            error_type: 'ml_diagnosis',
            needs_intervention: false
        }
        
        // Record in the database (background/best-effort) to keep the learning flow intact
        try {
            const submission = await submitAnswer(evidence.questionId, evidence.code || evidence.output)
            return { diagnosis, submissionId: submission.id }
        } catch (e) {
            return { diagnosis, submissionId: diagnosis.id }
        }
    }
    const submission = await submitAnswer(evidence.questionId, evidence.code || evidence.output)
    return { diagnosis: submission.diagnosis, submissionId: submission.id }
  },
}
export const existingInterventionAdapter: InterventionAdapter = { create: makeIntervention }

/** Extension seams only: no ML model or RAG retrieval is invoked at this checkpoint. */
export const recommendationAdapter: RecommendationAdapter = { async nextTask() { return null } }
export const learningResourceAdapter: LearningResourceAdapter = { async getResource() { return null } }
