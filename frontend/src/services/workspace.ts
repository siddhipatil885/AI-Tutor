import { evaluateTask, initialWorkspaceState, project, type EngineeringTask, type WorkspaceState } from '../domain/workspace.ts'

const storageKey = 'relearn.workspace.v2'
export function loadWorkspace(): WorkspaceState {
  try {
    const raw = localStorage.getItem(storageKey)
    if (!raw) return initialWorkspaceState()
    const saved = JSON.parse(raw) as Partial<WorkspaceState>
    const initial = initialWorkspaceState()
    return { ...initial, ...saved, files: { ...initial.files, ...saved.files }, committedFiles: { ...initial.committedFiles, ...saved.committedFiles } }
  } catch { return initialWorkspaceState() }
}
export function saveWorkspace(state: WorkspaceState) {
  try { localStorage.setItem(storageKey, JSON.stringify(state)) } catch { /* Keep editing if browser storage is unavailable. */ }
}
export function runTaskChecks(task: EngineeringTask, state: WorkspaceState) {
  const results = evaluateTask(task, state.files)
  const preview = previewTask(task, state.files)
  return { results, preview, allPassed: results.length > 0 && results.every(result => result.passed) }
}
export function previewTask(task: EngineeringTask, files: Record<string, string>) {
  if (task.id !== 'RL-1042') return 'This ticket does not define a program output preview.'
  const source = files['src/sequence.py'] || ''
  return /range\(\s*start\s*,\s*stop\s*\+\s*1\s*\)/.test(source) ? '1 2 3' : '1 2'
}
export function limitedTerminal(command: string, state: WorkspaceState, activeTask: EngineeringTask) {
  const [name, ...args] = command.trim().split(/\s+/)
  if (name === 'help') return 'Available commands: ls, cat <file>, git status, git log, python main.py, pytest'
  if (name === 'ls' && args.length === 0) return project.files.map(file => file.path).join('\n')
  if (name === 'cat' && args.length === 1) {
    const path = args[0]
    return state.files[path] ?? `No project file named ${path || '(empty)'}. Use ls to view available files.`
  }
  if (name === 'git' && args.length === 1 && args[0] === 'status') return `Modified files:\n${Object.keys(state.files).filter(path => state.files[path] !== state.committedFiles[path]).map(path => ` M ${path}`).join('\n') || 'working tree clean'}`
  if (name === 'git' && args.length === 1 && args[0] === 'log') return state.commits.map(commit => `${commit.id} ${commit.message}`).join('\n') || 'No commits yet.'
  if (name === 'python' && args.length === 1 && args[0] === 'main.py') return `Use the workspace Run action for the ${activeTask.kind} task's bounded output preview. Arbitrary Python execution is disabled.`
  if (name === 'pytest' && args.length === 0) {
    const results = evaluateTask(activeTask, state.files)
    return results.map(result => `${result.passed ? 'PASS' : 'FAIL'} ${result.id}: ${result.detail}`).join('\n')
  }
  if (name === 'gcc' || name === 'g++') return 'C/C++ syntax editing is supported by the editor, but no isolated compiler is configured in this project.'
  return `Command not available: ${command}. Type help for the allowlisted workspace commands.`
}
