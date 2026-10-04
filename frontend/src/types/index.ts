export type Question = { id: number; concept_id: string; prompt: string; expected_answer: string; explanation: string; difficulty: string; question_kind: string }
export type Diagnosis = { id?: number; is_correct: boolean; misconception_id?: string; misconception_name?: string; confidence: number; evidence: string[]; error_type: string; needs_intervention: boolean }
export type Intervention = { id: number; diagnosis_id: number; misconception_id: string; title: string; what_happened: string; explanation: string; worked_example: string; guided_hint: string; sources: string[] }
export type Assessment = { assessment_id: number; question: Question; status: 'pending' | 'unresolved' | 'improving' | 'resolved' | 'uncertain'; evidence: string[] }
export type Learner = { user_id: number; mastery: Record<string, number>; active_misconceptions: string[]; resolved_misconceptions: string[]; trajectory: {status: string; misconception_id: string; evidence: string[]}[] }
export type JudgeResult = {
  passed: boolean;
  problem_id: string;
  function_name: string;
  failed_tests: Array<{ index: number; input: unknown[] | null; expected: unknown; actual: unknown; error: string }>;
  compiler_error: boolean;
  runtime_error: boolean;
}
