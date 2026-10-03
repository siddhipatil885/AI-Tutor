import type { EngineeringTask, SkillName, WorkspaceState } from '../domain/workspace'

export const progressionConfig = {
  levels: [
    { name:'Coding foundations', xp:0 }, { name:'Bug fixer', xp:100 }, { name:'Junior developer', xp:250 },
    { name:'Feature builder', xp:450 }, { name:'Debugging specialist', xp:700 }, { name:'Test engineer', xp:1000 },
    { name:'Code reviewer', xp:1350 }, { name:'Backend developer', xp:1750 }, { name:'Full-stack developer', xp:2200 }, { name:'Software engineer', xp:2700 },
  ],
  rewards: { taskCompleted:50, testsPassing:40, regressionTest:30, commit:5, reviewCompleted:30, hintUsed:5, predictionAccurate:15 } as const,
}

export function totalXp(state: WorkspaceState) { return state.xpEvents.reduce((total, event) => total + event.amount, 0) }
export function currentLevel(state: WorkspaceState) {
  const xp = totalXp(state)
  return progressionConfig.levels.reduce((level, candidate, index) => xp >= candidate.xp ? index : level, 0)
}
export function xpToNextLevel(state: WorkspaceState) {
  const level = currentLevel(state)
  const next = progressionConfig.levels[level + 1]
  return next ? { current: totalXp(state) - progressionConfig.levels[level].xp, required: next.xp - progressionConfig.levels[level].xp, nextName: next.name } : null
}
export function reward(state: WorkspaceState, id: string, amount: number, reason: string): WorkspaceState {
  if (state.xpEvents.some(event => event.id === id)) return state
  return { ...state, xpEvents: [...state.xpEvents, { id, amount, reason }] }
}
export function rewardForTask(state: WorkspaceState, task: EngineeringTask): WorkspaceState {
  let next = reward(state, `task:${task.id}`, progressionConfig.rewards.taskCompleted, `${task.title} completed`)
  next = reward(next, `tests:${task.id}`, progressionConfig.rewards.testsPassing, 'All task checks passed')
  if (task.kind === 'testing') next = reward(next, `regression:${task.id}`, progressionConfig.rewards.regressionTest, 'Regression test added')
  if (task.kind === 'bug' && next.signals.some(signal => signal.taskId === task.id && signal.kind === 'run' && !signal.passed)) next = reward(next, `debug:${task.id}`, 25, 'Bug reproduced before the fix')
  if (next.hintsUsed[task.id] === undefined) next = reward(next, `independent:${task.id}`, 15, 'Completed without a hint')
  return next
}
export function maybeUnlockAchievements(state: WorkspaceState): WorkspaceState {
  const earned = new Set(state.achievements)
  const tasks = state.completedTaskIds
  if (tasks.includes('RL-1042') && state.signals.some(signal => signal.taskId === 'RL-1042' && signal.kind === 'run' && signal.passed === false)) earned.add('first-bug-fix')
  if (tasks.includes('RL-1043')) earned.add('first-regression-test')
  if (state.commits.length && state.xpEvents.some(event => event.id.startsWith('commit:'))) earned.add('first-commit')
  if (state.reviewCompleted) earned.add('first-code-review')
  if (tasks.includes('RL-1044')) earned.add('first-feature')
  if (['RL-1042','RL-1043','RL-1044'].every(taskId => tasks.includes(taskId))) earned.add('project-shipped')
  return { ...state, achievements: [...earned] }
}
export function skillScore(state: WorkspaceState, skill: SkillName) {
  const relevant = state.signals.filter(signal => {
    if (skill === 'Code review') return signal.kind === 'review'
    if (skill === 'Git') return state.commits.length > 0
    const task = signal.taskId
    return (skill === 'Debugging' && task === 'RL-1042') || (skill === 'Testing' && task === 'RL-1043') || (skill === 'Programming' && task === 'RL-1044') || (skill === 'Problem solving' && ['RL-1042','RL-1043','RL-1044'].includes(task)) || (skill === 'Documentation' && state.commits.some(commit => commit.files.includes('README.md')))
  })
  const complete = relevant.filter(signal => signal.kind === 'submit' && signal.passed).length
  const reviews = skill === 'Code review' && state.reviewCompleted ? 1 : 0
  const commits = skill === 'Git' ? state.commits.length : 0
  return Math.min(100, 15 + complete * 30 + reviews * 50 + commits * 10)
}
