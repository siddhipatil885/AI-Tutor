export type TaskKind = 'bug' | 'testing' | 'feature'
export type SkillName = 'Programming' | 'Debugging' | 'Testing' | 'Git' | 'Code review' | 'Documentation' | 'Problem solving'
export type ProjectFile = { path: string; language: string; content: string }
export type AcceptanceCheck = { id: string; label: string }
export type EngineeringTask = {
  id: string; number: string; kind: TaskKind; title: string; priority: 'Low' | 'Medium' | 'High';
  summary: string; why: string; requirements: string[]; acceptance: AcceptanceCheck[];
  relevantFiles: string[]; difficulty: string; conceptId?: string; skill: SkillName; unlockAfter?: string;
  hintLadder: string[]
}
export type EngineeringProject = { id: string; name: string; description: string; files: ProjectFile[]; tasks: EngineeringTask[] }
export type WorkspaceCommit = { id: string; message: string; files: string[]; createdAt: string }
export type AttemptSignal = { taskId: string; at: string; kind: 'run' | 'submit' | 'hint' | 'review'; passed?: boolean; hintLevel?: number; predictionAccurate?: boolean; error?: string }
export type ReviewComment = { issueId: string; line: number; text: string }
export type WorkspaceState = {
  files: Record<string, string>; completedTaskIds: string[]; committedFiles: Record<string, string>;
  commits: WorkspaceCommit[]; xpEvents: { id: string; amount: number; reason: string }[];
  achievements: string[]; signals: AttemptSignal[]; reviewComments: ReviewComment[];
  reviewCompleted: boolean; hintsUsed: Record<string, number>; prediction: string;
}

export const project: EngineeringProject = {
  id: 'relearn-loops', name: 'Loopback Tasks API',
  description: 'A small Python service for returning task sequences. Build confidence by fixing a boundary bug, adding a regression check, then shipping a helper.',
  files: [
    { path: 'src/sequence.py', language: 'python', content: '# Return the values from start through stop.\ndef values_between(start, stop):\n    return list(range(start, stop))\n' },
    { path: 'tests/test_sequence.py', language: 'python', content: 'import unittest\nfrom src.sequence import values_between\n\nclass SequenceTests(unittest.TestCase):\n    def test_empty_range(self):\n        self.assertEqual(values_between(2, 2), [])\n' },
    { path: 'README.md', language: 'markdown', content: '# Loopback Tasks API\n\nA learning project about reliable sequence boundaries.\n\nRun the focused task checks from the Re:Learn workspace.\n' },
  ],
  tasks: [
    { id: 'RL-1042', number: '#1042', kind: 'bug', title: 'Fix the inclusive end boundary', priority: 'High', difficulty: 'Beginner', conceptId: 'C001', skill: 'Debugging', summary: 'The sequence endpoint drops the last requested value.', why: 'Clients expect both the first and final values when requesting a closed interval.', requirements: ['Reproduce the missing final value.', 'Correct the boundary while preserving empty-range behavior.'], acceptance: [{id:'boundary',label:'values_between(1, 3) returns 1, 2, 3.'},{id:'empty',label:'An empty interval still returns an empty list.'}], relevantFiles: ['src/sequence.py','tests/test_sequence.py'], hintLadder: ['Compare the expected sequence with the current result.', 'Python range excludes its stop value.', 'For an inclusive public end, the stop passed to range needs to move one step forward.', 'Trace values_between(1, 3) by hand before editing.'] },
    { id: 'RL-1043', number: '#1043', kind: 'testing', title: 'Add a regression test for the final value', priority: 'Medium', difficulty: 'Beginner', skill: 'Testing', summary: 'Keep the boundary fix from regressing when this helper changes.', why: 'A targeted test makes the expected public behavior visible to the next developer.', requirements: ['Add a named test for a non-empty interval.', 'Assert both the first and final values.'], acceptance: [{id:'regression-test',label:'A focused test asserts the complete [1, 2, 3] result.'}], relevantFiles: ['tests/test_sequence.py'], unlockAfter: 'RL-1042', hintLadder: ['A regression test should fail before the fix and pass after it.', 'Use an assertion that compares the full returned list.', 'Include the stop value in the expected result.'] },
    { id: 'RL-1044', number: '#1044', kind: 'feature', title: 'Add a formatted sequence helper', priority: 'Low', difficulty: 'Intermediate', skill: 'Programming', summary: 'Expose a compact string representation for the sequence endpoint.', why: 'Callers need a stable, readable representation for logs and small responses.', requirements: ['Add format_sequence(start, stop).', 'Return values separated by a single space.'], acceptance: [{id:'format-helper',label:'format_sequence(1, 3) returns "1 2 3".'},{id:'empty-format',label:'An empty interval returns an empty string.'}], relevantFiles: ['src/sequence.py','tests/test_sequence.py'], unlockAfter: 'RL-1043', hintLadder: ['Reuse the existing sequence helper instead of duplicating boundary logic.', 'Convert each value to text, then join using one space.', 'Joining an empty list naturally produces an empty string.'] },
  ],
}

export const initialWorkspaceState = (): WorkspaceState => {
  const files = Object.fromEntries(project.files.map(file => [file.path, file.content]))
  return { files, completedTaskIds: [], committedFiles: { ...files }, commits: [], xpEvents: [], achievements: [], signals: [], reviewComments: [], reviewCompleted: false, hintsUsed: {}, prediction: '' }
}

export const supportedEditorLanguages = ['python','c','cpp','html'] as const
export function languageForPath(path: string) {
  const extension = path.split('.').pop()?.toLowerCase()
  if (extension === 'py') return 'python'
  if (extension === 'c') return 'c'
  if (extension === 'cpp' || extension === 'cc' || extension === 'cxx') return 'cpp'
  if (extension === 'html' || extension === 'htm') return 'html'
  if (extension === 'md') return 'markdown'
  return 'plaintext'
}
export function starterForPath(path: string) {
  const language = languageForPath(path)
  if (language === 'python') return '# Start your Python work here.\n'
  if (language === 'c') return '#include <stdio.h>\n\nint main(void) {\n    printf("Hello, Re:Learn!\\n");\n    return 0;\n}\n'
  if (language === 'cpp') return '#include <iostream>\n\nint main() {\n    std::cout << "Hello, Re:Learn!\\n";\n    return 0;\n}\n'
  if (language === 'html') return '<!doctype html>\n<html lang="en">\n  <head><meta charset="utf-8"><title>Learning page</title></head>\n  <body><main><h1>Hello, Re:Learn!</h1></main></body>\n</html>\n'
  if (language === 'markdown') return '# Project notes\n\nDescribe your change here.\n'
  return ''
}

export function isTaskUnlocked(task: EngineeringTask, state: WorkspaceState) {
  return !task.unlockAfter || state.completedTaskIds.includes(task.unlockAfter)
}

export function listModifiedFiles(state: WorkspaceState) {
  return Object.entries(state.files).filter(([path, value]) => value !== state.committedFiles[path]).map(([path]) => path)
}

export type CheckResult = { id: string; label: string; passed: boolean; detail: string }

/** Deterministic checks for the shipped learning fixtures; never evaluates learner source code. */
export function evaluateTask(task: EngineeringTask, files: Record<string, string>): CheckResult[] {
  const source = files['src/sequence.py'] || ''
  const tests = files['tests/test_sequence.py'] || ''
  const checks = {
    'boundary': /range\(\s*start\s*,\s*stop\s*\+\s*1\s*\)/.test(source),
    'empty': /if\s+start\s*>=\s*stop\s*:/.test(source) && /range\(\s*start\s*,\s*stop\s*\+\s*1\s*\)/.test(source),
    'regression-test': /def\s+test_\w+/.test(tests) && /assertEqual\s*\([^\n]*\[\s*1\s*,\s*2\s*,\s*3\s*\]/.test(tests),
    'format-helper': /def\s+format_sequence\s*\(/.test(source) && /' '\.join|" "\.join/.test(source),
    'empty-format': /def\s+format_sequence\s*\(/.test(source) && /join\s*\(/.test(source),
  }
  return task.acceptance.map(check => {
    const passed = Boolean(checks[check.id as keyof typeof checks])
    return { id: check.id, label: check.label, passed, detail: passed ? 'Acceptance condition found.' : 'This acceptance condition is not met yet.' }
  })
}

export const reviewPullRequest = {
  id: 'PR-0082', title: 'Fix the inclusive sequence boundary', description: 'Review the proposed loop-boundary fix before it is merged.',
  lines: [
    { number: 24, code: 'def values_between(start, stop):', issueId: 'empty-interval', issue: 'The empty interval must not include its start value.' },
    { number: 25, code: '    if start > stop:', issueId: 'empty-interval', issue: 'The equal-boundary case also needs to return an empty list.' },
    { number: 26, code: '        return []', issueId: 'return', issue: 'The guard returns an empty list.' },
    { number: 27, code: '    return list(range(start, stop))', issueId: 'exclusive-stop', issue: 'Python range excludes stop, so this drops the requested final value.' },
  ],
  expectedIssues: ['empty-interval','exclusive-stop'],
}

export function evaluateReview(comments: ReviewComment[]) {
  const found = new Set(comments.map(comment => comment.issueId))
  return reviewPullRequest.expectedIssues.every(issue => found.has(issue)) && comments.filter(comment => comment.text.trim().length >= 12).length >= 2
}

export const engineeringSkills: { name: SkillName; description: string; taskKinds: TaskKind[] }[] = [
  { name:'Programming', description:'Implement behavior', taskKinds:['feature'] },
  { name:'Debugging', description:'Reproduce and fix defects', taskKinds:['bug'] },
  { name:'Testing', description:'Protect behavior with checks', taskKinds:['testing'] },
  { name:'Git', description:'Track and describe changes', taskKinds:[] },
  { name:'Code review', description:'Find risks in a change', taskKinds:[] },
  { name:'Documentation', description:'Explain project behavior', taskKinds:[] },
  { name:'Problem solving', description:'Plan a safe approach', taskKinds:['bug','testing','feature'] },
]
