import { useEffect, useMemo, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import Editor from '@monaco-editor/react'
import { answerReassessment, getLearner, getQuestion, judgePythonSubmission, makeIntervention, startReassessment, submitAnswer } from './services/api'
import type { Assessment, Diagnosis, Intervention, JudgeResult, Learner, Question } from './types'
import { engineeringSkills, evaluateReview, isTaskUnlocked, languageForPath, listModifiedFiles, project, reviewPullRequest, starterForPath, type EngineeringTask, type ReviewComment, type WorkspaceState } from './domain/workspace'
import { currentLevel, maybeUnlockAchievements, progressionConfig, reward, rewardForTask, skillScore, totalXp, xpToNextLevel } from './services/progression'
import { limitedTerminal, loadWorkspace, previewTask, runTaskChecks, saveWorkspace } from './services/workspace'
import { existingDiagnosisAdapter, existingInterventionAdapter } from './services/learningAdapters'
import { announceAuthState, getCurrentUser, journeyTourStorageKey, signIn, signOut, signUp, subscribeToAuthState } from './services/auth'
import { journeyTourSteps, studentFlowModes, type StudentFlowModeId } from './flow'
import './flow.css'

type View = 'landing' | 'project' | 'progress' | 'review' | 'learning'
type Panel = 'terminal' | 'tests' | 'source'

type AuthMode = 'signin' | 'signup'
type AuthUser = NonNullable<Awaited<ReturnType<typeof getCurrentUser>>>

export default function App() {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [authLoading, setAuthLoading] = useState(true)

  useEffect(() => {
    getCurrentUser()
      .then(currentUser => {
        setUser(currentUser)
        announceAuthState(currentUser ? { userId: String(currentUser.id) } : null)
      })
      .catch(() => {
        setUser(null)
        announceAuthState(null)
      })
      .finally(() => setAuthLoading(false))
  }, [])

  if (authLoading) return <div className="auth-loading">Checking your session...</div>
  if (!user) return <AuthScreen onAuthenticated={currentUser => { setUser(currentUser); announceAuthState({ userId: String(currentUser.id) }) }} />

  return (
    <LearningApp
      userId={String(user.id)}
      onLogout={async () => {
        await signOut()
        announceAuthState(null)
        setUser(null)
      }}
    />
  )
}

function LearningApp({ userId, onLogout }: { userId: string; onLogout: () => Promise<void> }) {
  const [workspace, setWorkspace] = useState<WorkspaceState>(loadWorkspace)
  const [view, setView] = useState<View>('landing')
  const [activeTaskId, setActiveTaskId] = useState(project.tasks[0].id)
  const [activeFile, setActiveFile] = useState(project.files[0].path)
  const [panel, setPanel] = useState<Panel>('terminal')
  const [terminal, setTerminal] = useState('Re:Learn project terminal · restricted command set. Type help.')
  const [command, setCommand] = useState('')
  const [checkResults, setCheckResults] = useState<ReturnType<typeof runTaskChecks>['results']>([])
  const [preview, setPreview] = useState('Run the project checks to see a bounded task preview.')
  const [notice, setNotice] = useState('')
  const [question, setQuestion] = useState<Question | null>(null)
  const [learner, setLearner] = useState<Learner | null>(null)
  const [diagnosis, setDiagnosis] = useState<Diagnosis | null>(null)
  const [intervention, setIntervention] = useState<Intervention | null>(null)
  const [prediction, setPrediction] = useState('')
  const [commitMessage, setCommitMessage] = useState('')
  const [loading, setLoading] = useState(false)
  const [problem, setProblem] = useState('')
  const [showCreateFile, setShowCreateFile] = useState(false)
  const [showJourneyTour, setShowJourneyTour] = useState(false)
  const [authenticatedUserId, setAuthenticatedUserId] = useState<string | null>(userId)
  const [newFilePath, setNewFilePath] = useState('src/notes.py')

  const activeTask = project.tasks.find(task => task.id === activeTaskId) ?? project.tasks[0]
  const activeFileModel = project.files.find(file => file.path === activeFile) ?? { path:activeFile, language:languageForPath(activeFile), content:'' }
  const modifiedFiles = useMemo(() => listModifiedFiles(workspace), [workspace])
  const xp = totalXp(workspace)
  const levelIndex = currentLevel(workspace)
  const level = progressionConfig.levels[levelIndex]
  const nextLevel = xpToNextLevel(workspace)
  const conceptReady = workspace.xpEvents.some(event => event.id === 'concept:C001')
  const firstTaskComplete = workspace.completedTaskIds.includes('RL-1042')

  useEffect(() => { saveWorkspace(workspace) }, [workspace])
  useEffect(() => subscribeToAuthState(session => {
    const userId = session?.userId ?? null
    setAuthenticatedUserId(userId)
    if (!userId) { setShowJourneyTour(false); return }
    try { setShowJourneyTour(window.localStorage.getItem(journeyTourStorageKey(userId)) !== 'true') }
    catch { setShowJourneyTour(true) }
  }), [])
  useEffect(() => { Promise.all([getQuestion(), getLearner()]).then(([q, p]) => { setQuestion(q); setLearner(p) }).catch(error => setProblem(error.message)) }, [])

  const setFile = (path: string, content: string) => setWorkspace(current => ({ ...current, files: { ...current.files, [path]: content } }))
  const createFile = (event: FormEvent) => {
    event.preventDefault()
    const path = newFilePath.trim()
    if (!/^(src|tests|examples|public)\/[A-Za-z0-9_-]+\.(py|c|cpp|html|md)$/.test(path)) { setProblem('Use a project path under src, tests, examples, or public with a .py, .c, .cpp, .html, or .md extension.'); return }
    if (Object.hasOwn(workspace.files, path)) { setProblem('A project file with that path already exists.'); return }
    const language = languageForPath(path)
    if (!['python','c','cpp','html','markdown'].includes(language)) return
    setWorkspace(current => ({ ...current, files:{ ...current.files, [path]:starterForPath(path) } }))
    setActiveFile(path); setView('project'); setShowCreateFile(false); setProblem(''); setNotice(`Created ${path}. Monaco has syntax support for ${language}.`)
  }
  const recordSignal = (signal: WorkspaceState['signals'][number]) => setWorkspace(current => ({ ...current, signals: [...current.signals, signal] }))
  const selectTask = (task: EngineeringTask) => { if (!isTaskUnlocked(task, workspace)) return; setActiveTaskId(task.id); setActiveFile(task.relevantFiles[0]); setCheckResults([]); setDiagnosis(null); setIntervention(null); setNotice(''); setView('project') }

  const run = () => {
    const output = previewTask(activeTask, workspace.files)
    setPreview(output)
    recordSignal({ taskId: activeTask.id, at: new Date().toISOString(), kind: 'run' })
    setPanel('terminal')
    setNotice('Output preview ready. Running a preview does not complete the task.')
    if (activeTask.id === 'RL-1042' && workspace.prediction.trim()) {
      const accurate = workspace.prediction.trim().replace(/\s+/g, ' ') === output
      if (accurate) setWorkspace(current => reward(current, `predict:${activeTask.id}`, progressionConfig.rewards.predictionAccurate, 'Accurate output prediction'))
      setWorkspace(current => ({ ...current, signals: [...current.signals, { taskId: activeTask.id, at: new Date().toISOString(), kind: 'run', predictionAccurate: accurate }] }))
    }
  }
  const runChecks = () => {
    const check = runTaskChecks(activeTask, workspace)
    setCheckResults(check.results)
    setPreview(`${check.preview}\n\n${check.results.map(result => `${result.passed ? 'PASS' : 'FAIL'} ${result.id}: ${result.detail}`).join('\n')}`)
    recordSignal({ taskId: activeTask.id, at: new Date().toISOString(), kind: 'run', passed: check.allPassed, error: check.allPassed ? undefined : 'Acceptance checks failed' })
    setPanel('tests')
    setNotice(check.allPassed ? 'Checks pass. Review the task, then submit when you are ready.' : 'Some checks failed. Use the feedback or a hint to guide the next change.')
  }

  const submitTask = async () => {
    const check = runTaskChecks(activeTask, workspace)
    setCheckResults(check.results)
    recordSignal({ taskId: activeTask.id, at: new Date().toISOString(), kind: 'submit', passed: check.allPassed })
    if (activeTask.id === 'RL-1042' && !question) { setProblem('The existing Re:Learn assessment API is unavailable. Your code is saved; retry after the backend is running.'); return }
    if (activeTask.id === 'RL-1042' && question) {
      setLoading(true); setProblem('')
      try {
        const source = workspace.files['src/sequence.py'] || ''
        const result = await existingDiagnosisAdapter.diagnose({ taskId:activeTask.id, conceptId:activeTask.conceptId, output:check.preview, code:source, allPassed: check.allPassed, userId:1, questionId:question.id })
        setDiagnosis(result.diagnosis)
        if (result.diagnosis.needs_intervention) setIntervention(await existingInterventionAdapter.create(result.submissionId))
        if (!result.diagnosis.is_correct) {
          setNotice(result.diagnosis.evidence[0]); setPanel('tests'); return
        }
        await getLearner().then(setLearner)
      } catch (error) { setProblem(error instanceof Error ? error.message : 'Could not submit this task. Your work is saved.'); return }
      finally { setLoading(false) }
    }
    if (!check.allPassed) { setPanel('tests'); setNotice('Submission needs more work. Each failed check points to one acceptance criterion.'); return }
    setWorkspace(current => {
      let next = { ...current, completedTaskIds: current.completedTaskIds.includes(activeTask.id) ? current.completedTaskIds : [...current.completedTaskIds, activeTask.id] }
      next = rewardForTask(next, activeTask)
      return maybeUnlockAchievements(next)
    })
    setNotice(`${activeTask.title} completed. Your next engineering task is now available.`)
    setPanel('tests')
  }

  const useHint = () => {
    const currentLevel = workspace.hintsUsed[activeTask.id] ?? 0
    const nextHint = Math.min(currentLevel + 1, activeTask.hintLadder.length)
    if (nextHint === currentLevel) { setNotice('You have reached the final hint for this ticket.'); return }
    setWorkspace(current => {
      let next = { ...current, hintsUsed: { ...current.hintsUsed, [activeTask.id]: nextHint }, signals: [...current.signals, { taskId: activeTask.id, at: new Date().toISOString(), kind: 'hint' as const, hintLevel: nextHint }] }
      return reward(next, `hint:${activeTask.id}:${nextHint}`, progressionConfig.rewards.hintUsed, `Hint level ${nextHint} used`)
    })
    setNotice(`Hint ${nextHint}: ${activeTask.hintLadder[nextHint - 1]}`)
  }

  const commit = () => {
    const message = commitMessage.trim()
    if (message.length < 8 || modifiedFiles.length === 0) { setNotice('Add a clear commit message (at least 8 characters) and make a project change first.'); return }
    setWorkspace(current => {
      const files = listModifiedFiles(current)
      let next = { ...current, committedFiles: { ...current.files }, commits: [...current.commits, { id: `c${String(current.commits.length + 1).padStart(3, '0')}`, message, files, createdAt: new Date().toISOString() }] }
      if (runTaskChecks(activeTask, current).allPassed) next = reward(next, `commit:${activeTask.id}`, progressionConfig.rewards.commit, 'Passing project change committed')
      if (files.includes('README.md') && Math.abs((current.files['README.md'] ?? '').length - (current.committedFiles['README.md'] ?? '').length) >= 20) next = reward(next, `docs:${activeTask.id}`, 15, 'Project documentation updated')
      return maybeUnlockAchievements(next)
    })
    setCommitMessage(''); setNotice(`Committed ${modifiedFiles.length} file${modifiedFiles.length === 1 ? '' : 's'}.${runTaskChecks(activeTask, workspace).allPassed?' +5 XP for a change that passes the task checks.':' Commit XP is awarded after a meaningful task check passes.'}`)
  }

  const runCommand = (event: FormEvent) => {
    event.preventDefault()
    const output = limitedTerminal(command, workspace, activeTask)
    setTerminal(current => `${current}\n$ ${command}\n${output}`)
    setCommand('')
  }

  const completeReview = (comments: ReviewComment[]) => {
    if (!evaluateReview(comments)) { setNotice('Find and explain both review issues before submitting your review.'); return }
    setWorkspace(current => {
      let next = { ...current, reviewComments: comments, reviewCompleted: true, signals: [...current.signals, { taskId: reviewPullRequest.id, at: new Date().toISOString(), kind: 'review' as const, passed: true }] }
      next = reward(next, 'review:pr-0082', progressionConfig.rewards.reviewCompleted, 'Code review completed')
      return maybeUnlockAchievements(next)
    })
    setNotice('Review submitted. You identified both blocking issues and earned review XP.')
  }

  const showLearning = () => { setView('learning'); setNotice('') }
  const openMode = (mode: StudentFlowModeId) => {
    setNotice('')
    if (mode === 'project' && !conceptReady) { setView('learning'); setNotice('Start with the loop-boundary question. A correct answer or transfer check opens the project task.'); return }
    if (mode === 'review' && !firstTaskComplete) { setView('project'); setNotice('Pass the first project task to unlock its pull-request review.'); return }
    setView(mode)
  }
  const recordConceptMastery = () => {
    setWorkspace(current => reward(current, 'concept:C001', 25, 'Loop boundary concept mastered'))
    getLearner().then(setLearner).catch(() => undefined)
  }
  const continueToProject = () => { setView('project'); setNotice('Concept check complete. Apply the loop-boundary idea to task #1042.'); }
  const closeJourneyTour = () => {
    setShowJourneyTour(false)
    try { if (authenticatedUserId) window.localStorage.setItem(journeyTourStorageKey(authenticatedUserId), 'true') }
    catch { /* The tour can still be dismissed for this visit. */ }
  }
  const goToDashboard = () => { setView('landing'); setNotice(''); setProblem('') }

  if (view === 'landing') {
    return <div className="landing-shell"><main className="dev-main landing-main"><LandingView onSelectMode={openMode} onShowTour={() => setShowJourneyTour(true)} xp={xp} level={level.name} mastery={Math.round((learner?.mastery.C001 ?? 0.35) * 100)} conceptReady={conceptReady} firstTaskComplete={firstTaskComplete} reviewComplete={workspace.reviewCompleted} /></main>{showJourneyTour && <JourneyTour onClose={closeJourneyTour} onStart={() => { closeJourneyTour(); openMode('learning') }} />}</div>
  }

  return <div className="dev-shell">
    <aside className="dev-sidebar">
      <div className="dev-brand"><span className="dev-mark">R</span><span>Re:Learn</span></div>
      <div className="workspace-label">DEVELOPER WORKSPACE</div>
      <button className="side-item" onClick={goToDashboard}><i className="bi bi-grid-1x2-fill"/>Dashboard</button>
      <button className={`side-item ${view === 'project' ? 'selected' : ''}`} onClick={() => openMode('project')}><i className="bi bi-code-square"/>Projects</button>
      <button className={`side-item ${view === 'progress' ? 'selected' : ''}`} onClick={() => setView('progress')}><i className="bi bi-graph-up"/>Progress</button>
      <button className={`side-item ${view === 'review' ? 'selected' : ''}`} onClick={() => openMode('review')}><i className="bi bi-check2-square"/>Code review</button>
      <button className={`side-item ${view === 'learning' ? 'selected' : ''}`} onClick={showLearning}><i className="bi bi-journal-code"/>Learning loop</button>
      <div className="project-tree"><span className="tree-heading"><i className="bi bi-chevron-down"/> {project.name.toUpperCase()}</span><span className="tree-sub">TICKETS · {project.tasks.length}</span>{project.tasks.map(task => <button key={task.id} disabled={!isTaskUnlocked(task, workspace)} className={`tree-task ${task.kind} ${activeTask.id === task.id && view === 'project' ? 'active' : ''} ${!isTaskUnlocked(task, workspace) ? 'locked' : ''}`} onClick={() => selectTask(task)}><i className={`bi ${task.kind === 'bug' ? 'bi-bug' : task.kind === 'feature' ? 'bi-stars' : 'bi-check2-circle'}`}/>{task.title}{workspace.completedTaskIds.includes(task.id) && <i className="task-complete bi bi-check-circle-fill"/>}</button>)}<span className="tree-sub files-head">REPOSITORY</span>{Object.keys(workspace.files).map(path => <button key={path} className={`tree-file ${activeFile === path ? 'file-active' : ''}`} onClick={() => {setActiveFile(path);setView('project')}}><i className="bi bi-file-code"/>{path.split('/').pop()}{workspace.files[path] !== workspace.committedFiles[path] && <span className="file-dot"/>}</button>)}<button className="new-file-button" onClick={()=>setShowCreateFile(true)}><i className="bi bi-plus"/>New file</button></div>
      <div className="dev-user"><span className="user-avatar">AL</span><span><strong>Alex Learner</strong><small>{level.name} · Level {levelIndex + 1}</small></span><button className="logout-button" onClick={() => { void onLogout() }} aria-label="Log out" title="Log out"><i className="bi bi-box-arrow-right"/></button></div>
    </aside>
    <main className="dev-main">
      <header className="dev-topbar"><div className="breadcrumbs"><button type="button" className="mini-back" onClick={goToDashboard}>← Dashboard</button><span>Projects</span><i className="bi bi-chevron-right"/><strong>{project.name}</strong><i className="bi bi-chevron-right"/><span>{view === 'review' ? 'Pull request' : view === 'progress' ? 'Progress' : view === 'learning' ? 'Learning loop' : activeTask.number}</span></div><div className="top-stats"><span className="level-chip"><i className="bi bi-stars"/>Level {levelIndex + 1} · {level.name}</span><span className="xp-chip">{xp} XP</span></div></header>
      {showCreateFile&&<div className="dialog-backdrop"><form className="new-file-dialog" role="dialog" aria-modal="true" aria-labelledby="new-file-title" onSubmit={createFile}><button type="button" className="dialog-close" onClick={()=>setShowCreateFile(false)} aria-label="Close">×</button><span className="workspace-label">PROJECT REPOSITORY</span><h2 id="new-file-title">Create a file</h2><p>Monaco supports Python, C, C++, and HTML editing in this workspace.</p><label htmlFor="new-file-path">Project path</label><input id="new-file-path" value={newFilePath} onChange={event=>setNewFilePath(event.target.value)} autoFocus/><div className="dialog-actions"><button type="button" className="secondary-button" onClick={()=>setShowCreateFile(false)}>Cancel</button><button className="primary-action">Create file</button></div></form></div>}
      {problem && <div className="notice problem"><i className="bi bi-exclamation-triangle"/>{problem}<button onClick={() => setProblem('')} aria-label="Dismiss">×</button></div>}
      {notice && <div className="notice"><i className="bi bi-info-circle"/>{notice}<button onClick={() => setNotice('')} aria-label="Dismiss">×</button></div>}
      {view === 'project' && workspace.completedTaskIds.includes(activeTask.id) && <div className="next-step-banner"><span><strong>Task shipped</strong> Your checks passed. Review the pull request to complete this learning loop.</span><button className="primary-action" onClick={() => setView('review')}>Continue to review <i className="bi bi-arrow-right"/></button></div>}
      {view === 'review' && workspace.reviewCompleted && <div className="next-step-banner"><span><strong>Review complete · +30 XP</strong> Your concept, implementation, and review now count toward one learning record.</span><button className="primary-action" onClick={() => setView('progress')}>View progress <i className="bi bi-arrow-right"/></button></div>}
      {view === 'project' && <ProjectView task={activeTask} workspace={workspace} activeFile={activeFileModel.path} fileContent={workspace.files[activeFileModel.path] ?? ''} onFile={setFile} onSelectFile={setActiveFile} onRun={run} onRunTests={runChecks} onSubmit={submitTask} onHint={useHint} busy={loading} checkResults={checkResults} preview={preview} diagnosis={diagnosis} intervention={intervention} setPrediction={value => { setPrediction(value); setWorkspace(current => ({ ...current, prediction: value })) }} prediction={prediction || workspace.prediction} panel={panel} setPanel={setPanel} terminal={terminal} command={command} setCommand={setCommand} runCommand={runCommand} commitMessage={commitMessage} setCommitMessage={setCommitMessage} onCommit={commit} modifiedFiles={modifiedFiles} />}
      {view === 'progress' && <ProgressView state={workspace} learner={learner} onProject={() => setView('project')} />}
      {view === 'review' && <ReviewView comments={workspace.reviewComments} completed={workspace.reviewCompleted} onSubmit={completeReview} />}
      {view === 'learning' && <LearningLoop onCorrect={recordConceptMastery} onProgress={async () => { try { setLearner(await getLearner()) } catch (error) { setProblem(error instanceof Error ? error.message : 'Could not refresh learning progress.') } setView('progress') }} />}
      {view === 'learning' && conceptReady && <div className="next-step-banner"><span><strong>Concept badge earned · +25 XP</strong> Take the idea into a real coding task.</span><button className="primary-action" onClick={continueToProject}>Continue to task <i className="bi bi-arrow-right"/></button></div>}
      <footer className="workspace-footer"><span><i className="bi bi-shield-lock"/> Learner code is checked against task fixtures; the browser and API never run arbitrary project code.</span><span>{project.description}</span></footer>
    </main>
  </div>
}

function AuthScreen({ onAuthenticated }: { onAuthenticated: (user: AuthUser) => void }) {
  const [mode, setMode] = useState<AuthMode>('signin')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy(true)
    setError('')
    const values = new FormData(event.currentTarget)
    const email = String(values.get('email') || '')
    const password = String(values.get('password') || '')
    try {
      if (mode === 'signup') {
        await signUp(email, password, String(values.get('name') || 'Learner'))
      } else {
        await signIn(email, password)
      }
      const user = await getCurrentUser()
      if (!user) throw new Error('Authentication succeeded, but no session was returned.')
      onAuthenticated(user)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Authentication failed. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="auth-loading auth-screen">
      <section className="auth-card">
        <div className="dev-brand"><span className="dev-mark">R</span><span>Re:Learn</span></div>
        <span className="workspace-label">SECURE LEARNING WORKSPACE</span>
        <h1>{mode === 'signin' ? 'Welcome back.' : 'Start learning with Re:Learn.'}</h1>
        <p>{mode === 'signin' ? 'Sign in to continue your guided learning journey.' : 'Create your Neon Auth account to save progress securely.'}</p>
        {error && <div className="notice problem">{error}</div>}
        <form onSubmit={submit} className="auth-form">
          {mode === 'signup' && <label>Full name<input name="name" required autoComplete="name" placeholder="Alex Learner" /></label>}
          <label>Email address<input name="email" required type="email" autoComplete="email" placeholder="you@example.com" /></label>
          <label>Password<input name="password" required type="password" minLength={8} autoComplete={mode === 'signup' ? 'new-password' : 'current-password'} placeholder="At least 8 characters" /></label>
          <button className="primary-action" disabled={busy}>{busy ? 'Authenticating...' : mode === 'signin' ? 'Sign in' : 'Create account'}</button>
        </form>
        <button className="auth-switch" onClick={() => { setMode(mode === 'signin' ? 'signup' : 'signin'); setError('') }}>
          {mode === 'signin' ? 'New to Re:Learn? Create an account' : 'Already have an account? Sign in'}
        </button>
      </section>
    </main>
  )
}

function LandingView({ onSelectMode, onShowTour, xp, level, mastery, conceptReady, firstTaskComplete, reviewComplete }: { onSelectMode: (mode: StudentFlowModeId) => void; onShowTour:()=>void; xp:number; level:string; mastery:number; conceptReady:boolean; firstTaskComplete:boolean; reviewComplete:boolean }) {
  const [activeIndex, setActiveIndex] = useState(0)
  useEffect(() => {
    const timer = window.setInterval(() => setActiveIndex(index => (index + 1) % studentFlowModes.length), 6000)
    return () => window.clearInterval(timer)
  }, [])
  const activeMode = studentFlowModes[activeIndex]
  const statusFor = (mode: StudentFlowModeId) => mode === 'learning' ? conceptReady ? 'Concept badge earned' : 'Start here' : mode === 'project' ? firstTaskComplete ? 'Task shipped' : conceptReady ? 'Ready to build' : 'Unlock with concept check' : mode === 'review' ? reviewComplete ? 'Review complete' : firstTaskComplete ? 'Ready to review' : 'Unlock after first task' : `${xp} XP · ${level}`
  return <section className="landing-screen flow-dashboard">
    <header className="landing-topbar flow-nav"><div className="landing-brand"><span className="dev-mark">R</span><span>Re:Learn</span></div><nav aria-label="Student dashboard"><span>Dashboard</span><button className="tour-reopen" type="button" onClick={onShowTour}><i className="bi bi-question-circle"/> How it works</button><button type="button" onClick={() => onSelectMode('learning')}>Start learning <i className="bi bi-arrow-right"/></button></nav></header>
    <div className="landing-hero flow-hero"><div className="hero-copy"><span className="workspace-label">YOUR LEARNING JOURNEY</span><h1>Understand it.<br/><em>Build it. Review it.</em></h1><p>One connected path from a concept question to a tested change, a pull-request review, and visible progress.</p><div className="hero-metrics"><span><strong>{xp}</strong> XP</span><span><strong>{mastery}%</strong> concept confidence</span><span><strong>{firstTaskComplete ? '1' : '0'}</strong> task shipped</span></div><button className="primary-action" onClick={() => onSelectMode(conceptReady ? 'project' : 'learning')}>{conceptReady ? 'Continue your journey' : 'Start with a question'} <i className="bi bi-arrow-right"/></button></div>
      <div className={`journey-feature ${activeMode.accent}`} aria-live="polite"><div className="journey-feature-top"><span>{activeMode.stage}</span><span className="feature-signal"><i className="bi bi-stars"/> ADAPTIVE PATH</span></div><h2>{activeMode.label}</h2><p>{activeMode.bridge}</p><div className="feature-preview"><div className="preview-heading"><span>{activeMode.id === 'learning' ? 'CONCEPT CHECK' : activeMode.id === 'project' ? 'ACCEPTANCE CHECKS' : activeMode.id === 'review' ? 'PULL REQUEST' : 'LEARNER PROFILE'}</span><strong>{activeMode.id === 'learning' ? 'Loop boundaries' : activeMode.id === 'project' ? 'Inclusive end boundary' : activeMode.id === 'review' ? 'PR-0082 · Open' : `${xp} XP · ${level}`}</strong></div><div className="preview-track"><span style={{width:activeMode.id === 'learning' ? `${mastery}%` : activeMode.id === 'project' ? firstTaskComplete ? '100%' : conceptReady ? '48%' : '12%' : activeMode.id === 'review' ? reviewComplete ? '100%' : firstTaskComplete ? '48%' : '8%' : `${Math.min(xp % 100, 100)}%`}}/></div><div className="preview-footer"><span><i className="bi bi-check-circle-fill"/> {statusFor(activeMode.id)}</span><button type="button" onClick={() => onSelectMode(activeMode.id)}>Open stage <i className="bi bi-arrow-up-right"/></button></div></div><div className="journey-dots" aria-label="Choose featured stage">{studentFlowModes.map((mode,index)=><button key={mode.id} type="button" className={index===activeIndex?'active':''} aria-label={`Show ${mode.label}`} aria-pressed={index===activeIndex} onClick={() => setActiveIndex(index)}/>)}</div></div>
    </div>
    <div className="flow-section-heading"><div><span className="workspace-label">FOUR CONNECTED STAGES</span><h2>Pick up where you are</h2></div><span>{statusFor('learning')} <i className="bi bi-arrow-right"/> {statusFor('project')} <i className="bi bi-arrow-right"/> {statusFor('review')}</span></div>
    <div className="landing-grid flow-grid">{studentFlowModes.map((mode,index)=><article key={mode.id} className={`landing-card flow-card ${mode.accent} ${index===activeIndex?'featured':''}`}><div className="landing-card-top"><span className="mode-pill">{mode.stage}</span><span className="mode-status">{statusFor(mode.id)}</span></div><h2>{mode.label}</h2><p>{mode.description}</p><small>{mode.detail}</small><button className="primary-action" onClick={() => onSelectMode(mode.id)}>{mode.id === 'project' && !conceptReady ? 'Build the concept first' : mode.id === 'review' && !firstTaskComplete ? 'See project task' : `Open ${mode.label.toLowerCase()}`} <i className="bi bi-arrow-right"/></button></article>)}</div>
  </section>
}

function JourneyTour({ onClose, onStart }: { onClose:()=>void; onStart:()=>void }) {
  const [step, setStep] = useState(0)
  const dialogRef = useRef<HTMLElement>(null)
  const closeButtonRef = useRef<HTMLButtonElement>(null)
  const current = journeyTourSteps[step]
  const move = (direction: number) => setStep(index => Math.max(0, Math.min(journeyTourSteps.length - 1, index + direction)))

  useEffect(() => { closeButtonRef.current?.focus() }, [])
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'ArrowRight') move(1)
      if (event.key === 'ArrowLeft') move(-1)
      if (event.key === 'Escape') onClose()
      if (event.key === 'Tab') {
        const buttons = dialogRef.current?.querySelectorAll<HTMLElement>('button:not(:disabled)')
        const first = buttons?.[0]
        const last = buttons?.[buttons.length - 1]
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus() }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus() }
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [onClose])

  return <div className="tour-backdrop" onMouseDown={event => { if (event.target === event.currentTarget) onClose() }}>
    <section ref={dialogRef} className="journey-tour" role="dialog" aria-modal="true" aria-labelledby="tour-title" aria-describedby="tour-description">
      <button ref={closeButtonRef} className="tour-close" type="button" onClick={onClose} aria-label="Close walkthrough"><i className="bi bi-x-lg"/></button>
      <aside className="tour-mentor"><span className="tour-eyebrow">YOUR RE:LEARN GUIDE</span><TeacherDog/><strong>Professor Paws</strong><p>Small steps. Real progress.</p><div className="tour-progress-dots" aria-label={`Step ${step + 1} of ${journeyTourSteps.length}`}>{journeyTourSteps.map((item,index)=><span key={item.stage} className={index===step?'active':''}/>)}</div></aside>
      <div className="tour-content"><div className="tour-step-meta"><span>{current.stage}</span><span>{String(step + 1).padStart(2,'0')} / {String(journeyTourSteps.length).padStart(2,'0')}</span></div><div className="tour-icon"><i className={`bi ${current.icon}`}/></div><h2 id="tour-title">{current.title}</h2><p className="tour-description" id="tour-description">{current.description}</p><ul className="tour-details">{current.details.map(detail=><li key={detail}><i className="bi bi-check2"/>{detail}</li>)}</ul>{step===journeyTourSteps.length-1&&<p className="tour-note"><i className="bi bi-info-circle"/> This is a guided practice PR inside Re:Learn, not a GitHub account or external pull request.</p>}<div className="tour-controls"><button className="tour-skip" type="button" onClick={onClose}>Skip tour</button><div className="tour-arrow-controls"><button type="button" className="tour-arrow" onClick={()=>move(-1)} disabled={step===0} aria-label="Previous step"><i className="bi bi-arrow-left"/></button>{step<journeyTourSteps.length-1?<button type="button" className="tour-next" onClick={()=>move(1)}>Next <i className="bi bi-arrow-right"/></button>:<button type="button" className="tour-next" onClick={onStart}>Start with the quiz <i className="bi bi-arrow-right"/></button>}</div></div><span className="tour-key-hint">Use the arrow keys to move through the tour</span></div>
    </section>
  </div>
}

function TeacherDog() {
  return <svg className="teacher-dog" viewBox="0 0 200 190" role="img" aria-label="Professor Paws, the Re:Learn teacher dog">
    <ellipse cx="101" cy="171" rx="70" ry="9" fill="#12181a" opacity=".22"/>
    <path d="M48 135c-8 12-9 24-3 31h108c6-10 2-22-7-33" fill="#d98059" stroke="#1d2828" strokeWidth="5" strokeLinejoin="round"/>
    <path d="M62 141h78l12 26H49z" fill="#f1b58b" stroke="#1d2828" strokeWidth="5" strokeLinejoin="round"/>
    <path d="M75 143l24 15 25-15" fill="none" stroke="#1d2828" strokeWidth="4" strokeLinejoin="round"/>
    <path d="M53 67C32 39 16 48 24 76c5 16 17 24 31 22m92-31c21-28 37-19 29 9-5 16-17 24-31 22" fill="#a95f48" stroke="#1d2828" strokeWidth="6" strokeLinecap="round"/>
    <path d="M48 80c0-34 22-54 52-54s52 20 52 54-20 62-52 62S48 114 48 80z" fill="#f3d7b2" stroke="#1d2828" strokeWidth="6"/>
    <path d="M72 79a11 11 0 1 1 22 0" fill="none" stroke="#1d2828" strokeWidth="4" strokeLinecap="round"/>
    <path d="M107 79a11 11 0 1 1 22 0" fill="none" stroke="#1d2828" strokeWidth="4" strokeLinecap="round"/>
    <path d="M94 100c4-5 8-5 12 0l-6 7z" fill="#533c37"/>
    <path d="M100 107c-3 9-13 10-18 4m18-4c4 9 14 10 19 4" fill="none" stroke="#533c37" strokeWidth="3" strokeLinecap="round"/>
    <path d="M69 75h26m9 0h27m-36 0h9" fill="none" stroke="#49736b" strokeWidth="4" strokeLinecap="round"/>
    <path d="M71 48l30-17 30 17-30 17z" fill="#9be5d4" stroke="#1d2828" strokeWidth="5" strokeLinejoin="round"/>
    <path d="M81 47v14c10 9 29 9 39 0V47" fill="#74bcae" stroke="#1d2828" strokeWidth="4" strokeLinejoin="round"/>
    <path d="M102 30V20" stroke="#1d2828" strokeWidth="4" strokeLinecap="round"/>
    <circle cx="102" cy="17" r="5" fill="#f1b58b" stroke="#1d2828" strokeWidth="3"/>
    <path d="M38 158h40v12H38zm43 0h40v12H81z" fill="#8aa5a0" stroke="#1d2828" strokeWidth="4" strokeLinejoin="round"/>
    <path d="M52 151h74v10H52z" fill="#e7b864" stroke="#1d2828" strokeWidth="4" strokeLinejoin="round"/>
  </svg>
}

function ProjectView(props: {
  task: EngineeringTask; workspace: WorkspaceState; activeFile: string; fileContent: string; onFile: (path:string,content:string)=>void; onSelectFile:(path:string)=>void;
  onRun:()=>void; onRunTests:()=>void; onSubmit:()=>void; onHint:()=>void; busy:boolean; checkResults:ReturnType<typeof runTaskChecks>['results'];
  preview:string; diagnosis:Diagnosis|null; intervention:Intervention|null; prediction:string; setPrediction:(value:string)=>void;
  panel:Panel; setPanel:(panel:Panel)=>void; terminal:string; command:string; setCommand:(value:string)=>void; runCommand:(event:FormEvent)=>void;
  commitMessage:string; setCommitMessage:(value:string)=>void; onCommit:()=>void; modifiedFiles:string[]
}) {
  const {task,workspace}=props
  const hintLevel=workspace.hintsUsed[task.id]??0
  const language=languageForPath(props.activeFile)
  return <>
    <section className="task-banner"><div className="task-title"><span className={`issue-icon ${task.kind}`}><i className={`bi ${task.kind==='bug'?'bi-bug-fill':task.kind==='feature'?'bi-stars':'bi-check2-square'}`}/></span><div><div className="issue-meta"><span>{task.number}</span><span className={`issue-open ${workspace.completedTaskIds.includes(task.id)?'closed':''}`}>{workspace.completedTaskIds.includes(task.id)?'COMPLETED':'OPEN'}</span><span className="priority">{task.priority.toUpperCase()} · {task.difficulty.toUpperCase()}</span></div><h1>{task.title}</h1></div></div><p>{task.summary} <span className="why-line">{task.why}</span></p><div className="task-footer"><span><i className="bi bi-person-badge"/>{task.kind==='bug'?'QA report':task.kind==='feature'?'Product request':'Test request'}</span><span><i className="bi bi-diagram-3"/>{task.skill}</span><span><i className="bi bi-tag"/>{task.conceptId??'Engineering skill'}</span><span><i className="bi bi-lightning-charge"/>+50 XP</span></div></section>
    <div className="workspace-grid"><section className="editor-panel"><div className="panel-top"><div className="editor-tabs">{Object.keys(workspace.files).map(path=><button key={path} className={`file-tab ${props.activeFile===path?'active':''}`} onClick={()=>props.onSelectFile(path)}><i className="bi bi-file-code"/>{path.split('/').pop()}{workspace.files[path]!==workspace.committedFiles[path]&&<i className="bi bi-circle-fill dirty-dot"/>}</button>)}</div><span className="language-label">{language}</span></div><div className="monaco-wrap"><Editor height="365px" path={props.activeFile} language={language} value={props.fileContent} onChange={value=>props.onFile(props.activeFile,value??'')} theme="vs" options={{fontSize:12,lineHeight:21,fontFamily:'DM Mono, monospace',minimap:{enabled:false},scrollBeyondLastLine:false,wordWrap:'off',automaticLayout:true,tabSize:4,renderLineHighlight:'line',padding:{top:13},ariaLabel:`Code editor for ${props.activeFile}`}}/></div><div className="editor-actions"><span><i className="bi bi-cloud-check"/>Draft saved in this browser</span><span>{props.modifiedFiles.length} changed file{props.modifiedFiles.length===1?'':'s'}</span></div></section>
      <aside className="task-side"><div className="side-card"><div className="side-card-heading"><i className="bi bi-card-checklist"/>WHAT / WHY / ACCEPTANCE</div><p className="ticket-why">{task.why}</p><ul className="requirement-list">{task.requirements.map(requirement=><li key={requirement}>{requirement}</li>)}</ul><div className="criteria-list">{task.acceptance.map(check=>{const result=props.checkResults.find(item=>item.id===check.id);return <div className="criteria" key={check.id}><span className={result?.passed?'criterion done':result?'criterion failed':''}><i className={`bi ${result?.passed?'bi-check-circle-fill':result?'bi-x-circle-fill':'bi-circle'}`}/></span><p>{check.label}</p></div>})}</div>{props.diagnosis?.needs_intervention&&<div className="adaptive-feedback"><span>RELEARN INTERVENTION</span><strong>{props.intervention?.title??'Boundary pattern noticed'}</strong><p>{props.intervention?.explanation??props.diagnosis.evidence[0]}</p>{props.intervention&&<small>Try the hint ladder, then use Learning loop for a transfer check.</small>}</div>}<div className="task-actions"><button onClick={props.onRun}><i className="bi bi-play-fill"/>Run preview</button><button onClick={props.onRunTests}><i className="bi bi-check2-square"/>Run tests</button><button className="submit-task" disabled={props.busy||workspace.completedTaskIds.includes(task.id)} onClick={props.onSubmit}>{props.busy?'Submitting…':workspace.completedTaskIds.includes(task.id)?'Completed':'Submit task'}</button></div></div><div className="side-card hint-card"><div className="side-card-heading"><i className="bi bi-lightbulb"/>HINT LADDER · {hintLevel}/{task.hintLadder.length}</div>{hintLevel>0&&<p>{task.hintLadder[hintLevel-1]}</p>}<button className="text-button" onClick={props.onHint}>{hintLevel?'Show next hint':'Get a directional hint'} <span>+5 XP once per hint</span></button></div></aside></div>
    <div className="workflow-grid"><section className="console-panel"><div className="console-tabs"><button className={props.panel==='terminal'?'console-active':''} onClick={()=>props.setPanel('terminal')}><i className="bi bi-terminal"/>TERMINAL</button><button className={props.panel==='tests'?'console-active':''} onClick={()=>props.setPanel('tests')}><i className="bi bi-check2-square"/>TEST RESULTS</button><button className={props.panel==='source'?'console-active':''} onClick={()=>props.setPanel('source')}><i className="bi bi-git"/>SOURCE CONTROL {props.modifiedFiles.length>0&&<b>{props.modifiedFiles.length}</b>}</button></div>
      {props.panel==='terminal'&&<><div className="terminal-output">{props.terminal}<form onSubmit={props.runCommand} className="command-line"><span>$</span><input aria-label="Restricted project command" value={props.command} onChange={event=>props.setCommand(event.target.value)} placeholder="help"/><button>Run</button></form></div><div className="terminal-preview"><span>OUTPUT PREVIEW</span><pre>{props.preview}</pre></div></>}
      {props.panel==='tests'&&<div className="test-results"><div className="test-summary"><strong>{props.checkResults.filter(result=>result.passed).length} / {props.checkResults.length||task.acceptance.length} checks passed</strong><span>Fixture checks · {task.id}</span></div>{(props.checkResults.length?props.checkResults:task.acceptance.map(check=>({...check,passed:false,detail:'Not run yet.'}))).map(result=><div className="test-row" key={result.id}><i className={`bi ${result.passed?'bi-check-circle-fill':'bi-circle'}`}/><span><strong>{result.id}</strong><small>{result.label}</small></span><em>{result.passed?'passed':result.detail}</em></div>)}{props.diagnosis&&<div className="diagnosis-result"><strong>{props.diagnosis.is_correct?'ReLearn diagnosis: correct':'ReLearn noticed a boundary issue'}</strong><p>{props.diagnosis.evidence[0]}</p></div>}</div>}
      {props.panel==='source'&&<div className="source-control"><div><strong>Changed files</strong><small>{props.modifiedFiles.length?`${props.modifiedFiles.length} working change(s)`:'Working tree clean'}</small></div><ul>{props.modifiedFiles.map(path=><li key={path}><code>M</code>{path}</li>)}</ul><label htmlFor="commit-message">Commit message</label><input id="commit-message" value={props.commitMessage} onChange={event=>props.setCommitMessage(event.target.value)} placeholder="Describe the change"/><button disabled={!props.modifiedFiles.length} onClick={props.onCommit}><i className="bi bi-check2"/>Commit changes</button><div className="commit-history"><strong>Recent commits</strong>{workspace.commits.slice().reverse().slice(0,3).map(commit=><p key={commit.id}><code>{commit.id}</code> {commit.message}</p>)}{!workspace.commits.length&&<small>No commits yet. Commits are a learning simulation and do not create Git history.</small>}</div></div>}
    </section><aside className="task-side lower-side"><div className="side-card"><div className="side-card-heading"><i className="bi bi-person-lines-fill"/>TEAM NOTES</div><div className="team-note"><span>PM</span><p>Ship the agreed behavior with a clear acceptance check.</p></div><div className="team-note"><span>QA</span><p>{props.checkResults.some(result=>!result.passed)?'A task check is failing. Reproduce the issue and keep the regression case.':'Run the checks before submitting your change.'}</p></div><div className="team-note"><span>TECH LEAD</span><p>Keep the change focused and describe it in your commit.</p></div></div>{task.id==='RL-1042'&&<div className="side-card prediction-card"><div className="side-card-heading"><i className="bi bi-eye"/>PREDICT → CODE → RUN</div><label htmlFor="prediction">What output do you expect?</label><input id="prediction" value={props.prediction} onChange={event=>props.setPrediction(event.target.value)} placeholder="For example: 1 2 3"/><small>Make a prediction before running to record a useful learning signal.</small></div>}</aside></div>
  </>
}

function ProgressView({ state, learner, onProject }: { state:WorkspaceState; learner:Learner|null; onProject:()=>void }) {
  const xp=totalXp(state); const level=currentLevel(state); const progress=xpToNextLevel(state); const mastery=Math.round((learner?.mastery.C001??.35)*100)
  const achievementInfo=[['first-bug-fix','First bug fix','Reproduced and fixed a reported issue.'],['first-regression-test','Regression guard','Added a focused regression test.'],['first-feature','First feature','Shipped a requested behavior.'],['first-commit','First commit','Recorded a meaningful change.'],['first-code-review','Review complete','Identified both issues in a pull request.'],['project-shipped','Project shipped','Completed the linked bug, test, and feature tickets.']]
  return <section className="progress-view"><div className="progress-heading"><span className="workspace-label">ENGINEERING PROFILE</span><h1>{progressionConfig.levels[level].name}</h1><p>Progress grows from meaningful project work. Re:Learn's concept confidence remains connected to C001.</p></div><div className="profile-card"><div className="profile-level"><span>LEVEL {level+1}</span><strong>{xp} XP</strong><small>{progress?`${progress.current} / ${progress.required} XP to ${progress.nextName}`:'Top level reached'}</small></div><div className="mastery-track"><span style={{width:`${progress?progress.current/progress.required*100:100}%`}}/></div><div className="profile-stats"><div><small>CONCEPT CONFIDENCE</small><strong>{mastery}%</strong><span>Python loop boundaries · C001</span></div><div><small>TASKS SHIPPED</small><strong>{state.completedTaskIds.length} / {project.tasks.length}</strong><span>Project progression</span></div><div><small>COMMITS</small><strong>{state.commits.length}</strong><span>Simulated source control</span></div></div></div><div className="skills-card"><div className="section-heading"><h2>Engineering skills</h2><span>Evidence signals · connected to the canonical concept model</span></div><div className="skill-list">{engineeringSkills.map(skill=><div className="skill-row" key={skill.name}><span>{skill.name}</span><div className="mastery-track"><span style={{width:`${skillScore(state,skill.name)}%`}}/></div><strong>{skillScore(state,skill.name)}%</strong><small>{skill.description}</small></div>)}</div></div><div className="skills-card achievements"><div className="section-heading"><h2>Achievements</h2><span>{state.achievements.length} earned</span></div><div className="achievement-list">{achievementInfo.map(([id,title,description])=><div className={state.achievements.includes(id)?'earned':''} key={id}><i className={`bi ${state.achievements.includes(id)?'bi-patch-check-fill':'bi-lock'}`}/><span><strong>{title}</strong><small>{description}</small></span></div>)}</div></div><div className="skills-card evidence-card"><div className="section-heading"><h2>Learning evidence</h2><span>{state.signals.length} events saved locally</span></div><p>{learner?.trajectory.length?`${learner.trajectory.length} events in the existing adaptive learner record.`:'Task attempts, check results, hint use, prediction accuracy, and review outcomes are available through a local evidence adapter for future ML integration.'}</p><button className="secondary-button" onClick={onProject}>Return to project</button></div></section>
}

function CodeJudgePanel() {
  const defaultCode = `def two_sum(nums, target):
    seen = {}
    for index, value in enumerate(nums):
        need = target - value
        if need in seen:
            return [seen[need], index]
        seen[value] = index
    return []
`
  const [code,setCode]=useState(defaultCode)
  const [result,setResult]=useState<JudgeResult|null>(null)
  const [busy,setBusy]=useState(false)
  const [error,setError]=useState('')
  const challenge = { problem_id:'P001', function_name:'two_sum', tests:[{input:[[2,7,11,15],9], expected:[0,1]},{input:[[3,2,4],6], expected:[1,2]},{input:[[1,2,3],7], expected:[]}] }
  const submitCode = async () => {
    setBusy(true); setError(''); setResult(null)
    try {
      const next = await judgePythonSubmission({ ...challenge, code })
      setResult(next)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not judge this submission.')
    } finally {
      setBusy(false)
    }
  }
  const resetCode = () => { setCode(defaultCode); setResult(null); setError('') }

  return <article className="loop-card"><span className="loop-label">CODE JUDGE · PYTHON</span><h2>Two Sum challenge</h2><p>Read the prompt, type your solution, and click Run tests. The app checks your function against sample cases.</p><div className="task-actions" style={{marginBottom:'12px'}}><button className="secondary-button" onClick={resetCode}>Reset starter</button></div><ul className="requirement-list"><li>Return the index pair that sums to the target.</li><li>Use the first valid pair you find.</li><li>Return an empty list if no pair exists.</li></ul><label htmlFor="judge-code">Your Python solution</label><textarea id="judge-code" value={code} onChange={event=>setCode(event.target.value)} rows={14} placeholder="def two_sum(nums, target): ..."/><button className="secondary-button" disabled={busy} onClick={submitCode}>{busy?'Running tests…':'Run tests'}</button>{error&&<div className="notice problem">{error}</div>}{result&&<div className={`loop-feedback ${result.passed?'passed':''}`}><strong>{result.passed?'All test cases passed':'One or more tests failed'}</strong><p>{result.passed ? 'Your function matched the expected outputs.' : result.failed_tests[0] ? `First failing case: ${JSON.stringify(result.failed_tests[0].input)} -> expected ${JSON.stringify(result.failed_tests[0].expected)}, got ${JSON.stringify(result.failed_tests[0].actual)}` : 'The function did not satisfy the required behavior.'}</p>{!result.passed && result.failed_tests.length > 0 && <ul>{result.failed_tests.slice(0,3).map((failed, index) => <li key={`${failed.index}-${index}`}>Case {failed.index}: {failed.error}</li>)}</ul>}</div>}</article>
}

function ReviewView({ comments, completed, onSubmit }: { comments:ReviewComment[]; completed:boolean; onSubmit:(comments:ReviewComment[])=>void }) {
  const [selected,setSelected]=useState<Record<string,boolean>>(()=>Object.fromEntries(comments.map(comment=>[comment.issueId,true])))
  const [text,setText]=useState<Record<string,string>>(()=>Object.fromEntries(comments.map(comment=>[comment.issueId,comment.text])))
  const toggle=(id:string)=>setSelected(current=>({...current,[id]:!current[id]}))
  const active=reviewPullRequest.lines.filter((line,index)=>selected[line.issueId]&&line.issueId!=='return'&&reviewPullRequest.lines.findIndex(candidate=>candidate.issueId===line.issueId)===index)
  return <section className="review-view"><div className="progress-heading"><span className="workspace-label">PULL REQUEST · {reviewPullRequest.id}</span><h1>{reviewPullRequest.title}</h1><p>{reviewPullRequest.description} Identify at least two actionable issues and leave a line comment for each.</p></div><div className="review-banner"><i className="bi bi-git"/><div><strong>Review requested by the senior developer</strong><small>Focus on correctness, secrets, and behavior at the call site.</small></div><span>{completed?'REVIEWED':'OPEN'}</span></div><div className="review-code">{reviewPullRequest.lines.map((line,index)=><div className="review-line" key={line.number}><span>{line.number}</span><code>{line.code}</code>{line.issueId!=='return'&&reviewPullRequest.lines.findIndex(candidate=>candidate.issueId===line.issueId)===index&&<label><input type="checkbox" checked={Boolean(selected[line.issueId])} onChange={()=>toggle(line.issueId)}/> Mark for review</label>}</div>)}</div><div className="review-comments">{active.map(line=><div className="review-comment" key={line.issueId}><label htmlFor={`comment-${line.issueId}`}>Line {line.number} · comment</label><textarea id={`comment-${line.issueId}`} value={text[line.issueId]??''} onChange={event=>setText(current=>({...current,[line.issueId]:event.target.value}))} placeholder="Explain the risk and suggest a fix."/></div>)}</div><button className="primary-action" onClick={()=>onSubmit(active.map(line=>({issueId:line.issueId,line:line.number,text:text[line.issueId]??''})))} disabled={completed}>{completed?'Review complete':'Submit review · +30 XP'}</button><p className="review-hint">The review is scored against the two known issues in this teaching example.</p></section>
}

function LearningLoop({ onProgress, onCorrect }: { onProgress:()=>void|Promise<void>; onCorrect:()=>void }) {
  const [question,setQuestion]=useState<Question|null>(null);const [answer,setAnswer]=useState('');const [reasoning,setReasoning]=useState('');const [diagnosis,setDiagnosis]=useState<Diagnosis|null>(null);const [submissionId,setSubmissionId]=useState<number|null>(null);const [intervention,setIntervention]=useState<Intervention|null>(null);const [assessment,setAssessment]=useState<Assessment|null>(null);const [followup,setFollowup]=useState('');const [busy,setBusy]=useState(false);const [error,setError]=useState('')
  useEffect(()=>{getQuestion().then(setQuestion).catch(e=>setError(e.message))},[])
  const run=async(work:()=>Promise<void>)=>{setBusy(true);setError('');try{await work()}catch(e){setError(e instanceof Error?e.message:'Please try again.')}finally{setBusy(false)}}
  const submit=()=>run(async()=>{if(!question||!answer.trim())return;const result=await submitAnswer(question.id,answer,reasoning);setSubmissionId(result.id);setDiagnosis(result.diagnosis);if(result.diagnosis.is_correct)onCorrect()})
  const showIntervention=()=>run(async()=>{if(submissionId)setIntervention(await makeIntervention(submissionId))})
  const startFollowup=()=>run(async()=>{if(intervention)setAssessment(await startReassessment(intervention.id))})
  const answerFollowup=()=>run(async()=>{if(intervention&&assessment&&followup.trim()){const result=await answerReassessment(intervention.id,assessment.assessment_id,followup);setAssessment(result);if(result.status==='resolved')onCorrect()}})
  return <section className="learning-view"><div className="progress-heading"><span className="workspace-label">ADAPTIVE PRACTICE · C001</span><h1>Check your understanding</h1><p>The existing diagnose → intervene → reassess flow stays connected to the workspace.</p></div>{error&&<div className="notice problem">{error}</div>}{question&&<article className="loop-card"><span className="loop-label">PYTHON · LOOP BOUNDARIES</span><pre>{question.prompt}</pre><label htmlFor="loop-answer">Your answer</label><textarea id="loop-answer" value={answer} onChange={event=>setAnswer(event.target.value)} placeholder="For example: 1 2 3"/><details><summary>Add your reasoning (optional)</summary><textarea value={reasoning} onChange={event=>setReasoning(event.target.value)} placeholder="How did you work it out?"/></details>{diagnosis&&<div className={`loop-feedback ${diagnosis.is_correct?'passed':''}`}><strong>{diagnosis.is_correct?'Correct answer':diagnosis.misconception_name||'Answer checked'}</strong><p>{diagnosis.evidence[0]}</p></div>}{diagnosis?.needs_intervention&&!intervention&&<button className="secondary-button" disabled={busy} onClick={showIntervention}>Open focused explanation</button>}{intervention&&<div className="intervention-copy"><h2>{intervention.title}</h2><p>{intervention.explanation}</p><strong>Worked example</strong><p>{intervention.worked_example}</p><strong>Hint</strong><p>{intervention.guided_hint}</p>{!assessment&&<button className="secondary-button" disabled={busy} onClick={startFollowup}>Try a new example</button>}</div>}{assessment&&<div className="followup"><h2>Transfer check</h2><pre>{assessment.question.prompt}</pre>{assessment.status==='pending'?<><textarea value={followup} onChange={event=>setFollowup(event.target.value)} placeholder="Write the output values"/><button className="secondary-button" disabled={busy||!followup.trim()} onClick={answerFollowup}>Check answer</button></>:<div className="loop-feedback"><strong>{assessment.status}</strong><p>{assessment.evidence[0]}</p><button className="secondary-button" onClick={()=>void onProgress()}>See progress</button></div>}</div>}{!diagnosis&&<button className="primary-action" disabled={busy||!answer.trim()} onClick={submit}>{busy?'Checking…':'Check my thinking'}</button>}</article>}</section>
}
