export type StudentFlowModeId = 'learning' | 'project' | 'review' | 'progress'

export const journeyTourSteps = [
  {
    stage: '01 · Understand',
    title: 'Start with one small question',
    description: 'The quiz checks how you currently understand the idea. Answer in your own words or predict what the code prints.',
    details: ['Add your reasoning if you want the tutor to see how you got there.', 'A correct answer earns your concept badge and opens the project task.'],
    icon: 'bi-patch-question',
  },
  {
    stage: '02 · Get unstuck',
    title: 'A wrong answer is a route, not a dead end',
    description: 'Re:Learn looks for a supported misconception pattern. When it finds one, retrieval brings back a focused explanation, worked example, and hint.',
    details: ['Try the transfer question with different numbers.', 'Resolve the idea to earn the concept badge and continue. No XP is taken away.'],
    icon: 'bi-compass',
  },
  {
    stage: '03 · Build',
    title: 'Put the idea into code',
    description: 'The project task uses the same loop-boundary concept. Edit the code, run acceptance checks, and use hints when you need them.',
    details: ['Checks show which behavior passes and what still needs work.', 'When the required checks pass, submit the task to open its practice review.'],
    icon: 'bi-code-slash',
  },
  {
    stage: '04 · Review and grow',
    title: 'Finish with a practice pull request',
    description: 'Review a related proposed change, leave useful comments, and see your work add to one progress record.',
    details: ['Earn XP for concept mastery, shipped work, and useful review.', 'Your level, concept confidence, achievements, and next step live in Progress.'],
    icon: 'bi-git',
  },
] as const

export const studentFlowModes: Array<{
  id: StudentFlowModeId
  label: string
  description: string
  detail: string
  accent: string
  stage: string
  bridge: string
}> = [
  {
    id: 'learning',
    label: 'Guided learning',
    description: 'Use concept checks and adaptive support to build understanding.',
    detail: 'Best for: learning the idea before coding.',
    accent: 'green',
    stage: '01 · Understand',
    bridge: 'A concept question checks your starting point. If it is tricky, targeted guidance and a transfer check help you build confidence.',
  },
  {
    id: 'project',
    label: 'Project tasks',
    description: 'Solve realistic engineering tasks with tests, preview, and submission.',
    detail: 'Best for: applying skills in a real coding workflow.',
    accent: 'blue',
    stage: '02 · Build',
    bridge: 'Use what you learned to fix a real task. Acceptance checks decide when the change is ready to submit.',
  },
  {
    id: 'review',
    label: 'Code review',
    description: 'Read a pull request, find issues, and leave line-by-line comments.',
    detail: 'Best for: improving judgement and debugging patterns.',
    accent: 'orange',
    stage: '03 · Review',
    bridge: 'Review a pull request for actionable issues and earn experience for clear, evidence-based feedback.',
  },
  {
    id: 'progress',
    label: 'Progress',
    description: 'Track XP, level-ups, and mastery across the learning journey.',
    detail: 'Best for: seeing how far the student has come.',
    accent: 'purple',
    stage: '04 · Grow',
    bridge: 'Concept confidence, shipped tasks, review work, XP, and achievements all contribute to one learning record.',
  },
]
