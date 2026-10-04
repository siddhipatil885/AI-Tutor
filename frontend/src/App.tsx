import { FormEvent, useEffect, useState } from 'react'
import { getBackendHealth, getDatabaseHealth, getStudentAssignmentAttempts, getStudentAssignments, getStudentLabs, submitAssignment, submitLabProgress, type AssignmentAttempt, type StudentAssignment } from './services/api'
import { getCurrentUser, signIn, signOut, signUp } from './services/auth'
import InstitutionDashboard from './InstitutionDashboard'
import TeacherDashboard from './TeacherDashboard'

type View = 'home' | 'signin' | 'signup' | 'dashboard' | 'teacher' | 'institution'
type User = NonNullable<Awaited<ReturnType<typeof getCurrentUser>>>
type Status = 'checking' | 'connected' | 'unavailable'

const Logo = () => <div className="logo"><b>R</b><span>Re<span>:</span>Learn</span></div>
const routeFor = (view: View) => view === 'dashboard' ? '/dashboard' : view === 'teacher' ? '/teacher' : view === 'institution' ? '/institution' : view === 'home' ? '/' : `/${view}`
const viewForPath = (path: string): View => path === '/dashboard' ? 'dashboard' : path.startsWith('/teacher') ? 'teacher' : path === '/institution' ? 'institution' : path === '/signup' ? 'signup' : path === '/signin' ? 'signin' : 'home'

export default function App() {
  const [view, setView] = useState<View>(() => viewForPath(window.location.pathname))
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const navigate = (next: View) => { window.history.pushState({}, '', routeFor(next)); setView(next) }

  useEffect(() => {
    getCurrentUser().then(setUser).catch(() => setUser(null)).finally(() => setLoading(false))
  }, [])
  useEffect(() => {
    const onPopState = () => setView(viewForPath(window.location.pathname))
    window.addEventListener('popstate', onPopState)
    return () => window.removeEventListener('popstate', onPopState)
  }, [])
  useEffect(() => {
    if (!loading && view === 'dashboard' && !user) navigate('signin')
  }, [loading, user, view])
  useEffect(() => {
    if (!loading && view === 'teacher' && (!user || (user.role !== 'teacher' && user.role !== 'admin'))) {
      navigate(user ? 'dashboard' : 'signin')
    }
  }, [loading, user, view])
  useEffect(() => {
    if (!loading && view === 'dashboard' && user && (user.role === 'teacher' || user.role === 'admin')) {
      navigate('teacher')
    }
  }, [loading, user, view])
  useEffect(() => {
    if (!loading && view === 'institution' && !user) navigate('signin')
  }, [loading, user, view])

  if (loading) return <div className="auth-loading">Checking your session…</div>
  if (view === 'dashboard' && !user) return <div className="auth-loading">Redirecting to sign in…</div>
  if (view === 'teacher' && user && (user.role === 'teacher' || user.role === 'admin')) return <TeacherDashboard user={user} onLogout={async () => { await signOut(); setUser(null); navigate('signin') }} onInstitution={() => navigate('institution')} />
  if (view === 'teacher') return <div className="auth-loading">Redirecting to the correct workspace…</div>
  if (view === 'institution' && user) return <InstitutionDashboard user={user} onLogout={async () => { await signOut(); setUser(null); navigate('signin') }} onBack={() => navigate(user.role === 'teacher' || user.role === 'admin' ? 'teacher' : 'dashboard')} />
  if (view === 'home') return <Landing nav={navigate} />
  if (view === 'signin' || view === 'signup') return <Auth mode={view} nav={navigate} onAuthenticated={async () => { const nextUser = await getCurrentUser(); setUser(nextUser); navigate(nextUser && (nextUser.role === 'teacher' || nextUser.role === 'admin') ? 'teacher' : 'dashboard') }} />
  if (!user) return <div className="auth-loading">Redirecting to sign in…</div>
  return <Dashboard user={user} nav={navigate} onLogout={async () => { await signOut(); setUser(null); navigate('signin') }} />
}
function Landing({ nav }: { nav: (view: View) => void }) {
  return <div className="marketing"><nav><Logo/><div><a href="#loop">How it works</a><button className="plain" onClick={() => nav('signin')}>Sign in</button><button className="primary mini" onClick={() => nav('signup')}>Get started <i className="bi bi-arrow-up-right" /></button></div></nav><main className="hero"><section><span className="tag"><i className="bi bi-stars" /> ADAPTIVE LEARNING, MADE PERSONAL</span><h1>Understand the <em>why</em><br />behind every answer.</h1><p>Re:Learn is ready for its secure application foundation.</p><button className="primary" onClick={() => nav('signup')}>Start learning free <i className="bi bi-arrow-right" /></button></section></main></div>
}

function Auth({ mode, nav, onAuthenticated }: { mode: 'signin' | 'signup'; nav: (view: View) => void; onAuthenticated: () => Promise<void> }) {
  const signup = mode === 'signup'
  const [show, setShow] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError('')
    const values = new FormData(event.currentTarget)
    try {
      const email = String(values.get('email') || ''), password = String(values.get('password') || '')
      if (signup) await signUp(email, password, String(values.get('name') || 'Learner'))
      else await signIn(email, password)
      await onAuthenticated()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Authentication failed.')
    } finally { setBusy(false) }
  }
  return <div className="auth"><aside><Logo/><div className="auth-copy"><span className="tag"><i className="bi bi-stars" /> YOUR LEARNING, UNLOCKED</span><h1>Build on a<br />secure <em>foundation.</em></h1><p>Sign in to connect your React application to its FastAPI and Neon services.</p></div></aside><main><button className="back" onClick={() => nav('home')}><i className="bi bi-arrow-left" /> Back to home</button><section className="auth-form"><small>{signup ? 'CREATE YOUR ACCOUNT' : 'WELCOME BACK'}</small><h2>{signup ? 'Start with your account.' : 'Pick up where you left off.'}</h2><p>{signup ? 'Create a secure Neon Auth account.' : 'Sign in to continue to your dashboard.'}</p>{error && <div className="error">{error}</div>}<form onSubmit={submit}>{signup && <label>Full name<input name="name" required placeholder="Alex Learner" autoComplete="name" /></label>}<label>Email address<input name="email" required type="email" placeholder="you@example.com" autoComplete="email" /></label><label>Password<span className="password"><input name="password" required type={show ? 'text' : 'password'} minLength={8} placeholder="At least 8 characters" autoComplete={signup ? 'new-password' : 'current-password'} /><button type="button" onClick={() => setShow(!show)}><i className={`bi bi-eye${show ? '-slash' : ''}`} /></button></span></label><button disabled={busy} className="primary wide">{busy ? 'Authenticating…' : signup ? 'Create free account' : 'Sign in'} <i className="bi bi-arrow-right" /></button></form><p className="switch">{signup ? 'Already have an account?' : 'New to Re:Learn?'} <button onClick={() => nav(signup ? 'signin' : 'signup')}>{signup ? 'Sign in' : 'Create an account'}</button></p></section></main></div>
}

function Dashboard({ user, nav, onLogout }: { user: User; nav: (view: View) => void; onLogout: () => Promise<void> }) {
  const [backend, setBackend] = useState<Status>('checking')
  const [database, setDatabase] = useState<Status>('checking')
  const [assignments, setAssignments] = useState<StudentAssignment[]>([])
  const [labs, setLabs] = useState<Array<{ id: number; class_name: string; title: string; concept: string; instructions?: string; duration_minutes: number; status: string }>>([])
  const [assignmentError, setAssignmentError] = useState('')
  const [labsError, setLabsError] = useState('')
  const [assignmentsLoading, setAssignmentsLoading] = useState(true)
  const [labsLoading, setLabsLoading] = useState(true)
  const [labAnswers, setLabAnswers] = useState<Record<number, string>>({})
  const [submittingLab, setSubmittingLab] = useState<number | null>(null)
  const [labSubmitError, setLabSubmitError] = useState('')
  const [labSubmitNotice, setLabSubmitNotice] = useState('')
  const [refreshKey, setRefreshKey] = useState(0)
  const [activeSection, setActiveSection] = useState('overview')
  const [selectedAssignmentId, setSelectedAssignmentId] = useState<number | null>(null)
  const [assignmentAnswers, setAssignmentAnswers] = useState<Record<string, string>>({})
  const [assignmentAttempts, setAssignmentAttempts] = useState<AssignmentAttempt[]>([])
  const [assignmentSubmitBusy, setAssignmentSubmitBusy] = useState(false)
  const [assignmentSubmitError, setAssignmentSubmitError] = useState('')
  const [assignmentSubmitNotice, setAssignmentSubmitNotice] = useState('')
  useEffect(() => {
    getBackendHealth().then(result => setBackend(result.status === 'ok' ? 'connected' : 'unavailable')).catch(() => setBackend('unavailable'))
    getDatabaseHealth().then(result => setDatabase(result.status === 'ok' ? 'connected' : 'unavailable')).catch(() => setDatabase('unavailable'))
    setAssignmentsLoading(true)
    setLabsLoading(true)
    setAssignmentError('')
    setLabsError('')
    getStudentAssignments(user.id).then(setAssignments).catch(cause => {
      setAssignments([])
      setAssignmentError(cause instanceof Error ? cause.message : 'Assignments could not be loaded.')
    }).finally(() => setAssignmentsLoading(false))
    getStudentLabs(user.id).then(setLabs).catch(cause => {
      setLabs([])
      setLabsError(cause instanceof Error ? cause.message : 'Live labs could not be loaded.')
    }).finally(() => setLabsLoading(false))
  }, [user.id, refreshKey])
  useEffect(() => {
    if (selectedAssignmentId === null) {
      setAssignmentAttempts([])
      return
    }
    getStudentAssignmentAttempts(user.id, selectedAssignmentId).then(setAssignmentAttempts).catch(cause => {
      setAssignmentAttempts([])
      setAssignmentSubmitError(cause instanceof Error ? cause.message : 'Attempt history could not be loaded.')
    })
  }, [user.id, selectedAssignmentId, refreshKey])
  const label = (status: Status) => status === 'checking' ? 'Checking…' : status === 'connected' ? 'Connected' : 'Unavailable'
  const firstName = (user.name || 'Learner').split(' ')[0]
  const handleSubmitLab = async (labId: number) => {
    const answer = labAnswers[labId]?.trim()
    if (!answer || submittingLab !== null) return
    setSubmittingLab(labId)
    setLabSubmitError('')
    setLabSubmitNotice('')
    try {
      await submitLabProgress(user.id, labId, { answer, reflection: 'Student submitted a lab response in the live lab flow.' })
      setLabAnswers(current => ({ ...current, [labId]: '' }))
      setLabSubmitNotice('Lab response submitted.')
    } catch (cause) {
      setLabSubmitError(cause instanceof Error ? cause.message : 'The lab response could not be submitted.')
    } finally { setSubmittingLab(null) }
  }
  const publishedAssignments = assignments.filter(assignment => assignment.status.toLowerCase() === 'published')
  const activeLabs = labs.filter(lab => lab.status.toLowerCase() === 'active')
  const selectedAssignment = publishedAssignments.find(assignment => assignment.id === selectedAssignmentId)
  const handleSubmitAssignment = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!selectedAssignment || assignmentSubmitBusy) return
    if (selectedAssignment.questions.some(question => !assignmentAnswers[String(question.id)]?.trim())) {
      setAssignmentSubmitError('Answer each question before submitting.')
      return
    }
    setAssignmentSubmitBusy(true)
    setAssignmentSubmitError('')
    setAssignmentSubmitNotice('')
    try {
      const attempt = await submitAssignment(selectedAssignment.id, assignmentAnswers)
      setAssignmentAnswers({})
      setAssignmentAttempts(current => [...current, attempt])
      setAssignmentSubmitNotice(`Attempt ${attempt.attempt_number} submitted. Score: ${Math.round(attempt.score)}%. Grading uses exact answer matching.`)
    } catch (cause) {
      setAssignmentSubmitError(cause instanceof Error ? cause.message : 'Assignment could not be submitted.')
    } finally { setAssignmentSubmitBusy(false) }
  }
  const jumpTo = (section: string) => {
    setActiveSection(section)
    document.getElementById(section)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
  return <div className="app">
    <aside className="sidebar dashboard-sidebar">
      <Logo />
      <small>LEARNING SPACE</small>
      <button className={activeSection === 'overview' ? 'selected' : ''} onClick={() => jumpTo('overview')}><i className="bi bi-grid-1x2-fill" />Overview</button>
      <button className={activeSection === 'assignments' ? 'selected' : ''} onClick={() => jumpTo('assignments')}><i className="bi bi-journal-check" />Assignments</button>
      <button className={activeSection === 'labs' ? 'selected' : ''} onClick={() => jumpTo('labs')}><i className="bi bi-code-square" />Live labs</button>
      <button onClick={() => nav('institution')}><i className="bi bi-buildings" />Institution</button>
      <div className="profile">
        <b>{(user.name || user.email || 'U').slice(0, 2).toUpperCase()}</b>
        <span><strong>{user.name || 'Learner'}</strong><small>{user.email}</small></span>
        <button onClick={onLogout} aria-label="Log out"><i className="bi bi-box-arrow-right" /></button>
      </div>
    </aside>
    <main className="workspace dashboard-workspace">
      <header className="dashboard-header" id="overview">
        <div><small>LEARNING SPACE</small><h1>Welcome, {firstName}.</h1><p>Your assignments and live labs from enrolled classes.</p></div>
        <div className="header-actions"><button className="outline-button mini" onClick={() => setRefreshKey(key => key + 1)}><i className="bi bi-arrow-clockwise" /> Refresh</button></div>
      </header>
      <div className="dashboard-grid">
        <section className="dashboard-main">
          <section id="assignments">
            <div className="section-heading"><div><small>ASSIGNED WORK</small><h2>Assignments</h2></div></div>
            <div className="planner-card" style={{ marginTop: 12 }}>
              {assignmentsLoading ? <p>Loading assignments…</p> : assignmentError ? <p className="error" role="alert">{assignmentError}</p> : publishedAssignments.length ? publishedAssignments.map(assignment => <article className="student-assignment" key={assignment.id}>
                <button className="student-assignment-toggle" aria-expanded={selectedAssignmentId === assignment.id} onClick={() => { setSelectedAssignmentId(selectedAssignmentId === assignment.id ? null : assignment.id); setAssignmentAnswers({}); setAssignmentSubmitError(''); setAssignmentSubmitNotice('') }}>
                  <span className="planner-check"><i className="bi bi-journal-check" /></span>
                  <span><strong>{assignment.title}</strong><small>{assignment.class_name} · {assignment.difficulty} · {assignment.question_count} questions</small></span>
                  <i className={`bi ${selectedAssignmentId === assignment.id ? 'bi-chevron-up' : 'bi-chevron-down'}`} />
                </button>
                {selectedAssignmentId === assignment.id && <>
                  <form className="student-assignment-form" onSubmit={handleSubmitAssignment}>
                    {assignment.questions.map(question => <label key={question.id}>Question {question.id}<span>{question.prompt}</span><textarea required value={assignmentAnswers[String(question.id)] ?? ''} onChange={changeEvent => setAssignmentAnswers(current => ({ ...current, [String(question.id)]: changeEvent.target.value }))} placeholder="Your answer…" /></label>)}
                    {assignmentSubmitError && <p className="error" role="alert">{assignmentSubmitError}</p>}
                    {assignmentSubmitNotice && <p role="status">{assignmentSubmitNotice}</p>}
                    <button className="primary mini" disabled={assignmentSubmitBusy}>{assignmentSubmitBusy ? 'Submitting…' : 'Submit attempt'}</button>
                  </form>
                  {assignmentAttempts.length > 0 && <div className="student-attempt-history"><strong>Attempt history</strong>{assignmentAttempts.map(attempt => <details key={attempt.id}><summary>Attempt {attempt.attempt_number} · {Math.round(attempt.score)}%</summary>{attempt.feedback.map(result => <div key={result.question_id}><strong>Question {result.question_id}: {result.is_correct ? 'Correct' : 'Review'}</strong><p>Your answer: {result.answer}</p><p>Expected: {result.correct_answer}</p><small>{result.explanation}</small></div>)}</details>)}</div>}
                </>}
              </article>) : <p>No published assignments are available.</p>}
            </div>
          </section>
        </section>
        <aside className="dashboard-rail">
          <section id="labs" className="planner-card">
            <div className="card-heading"><div><small>CLASSROOM SESSIONS</small><h3>Live labs</h3></div></div>
            {labsLoading ? <p>Loading live labs…</p> : labsError ? <p className="error" role="alert">{labsError}</p> : activeLabs.length ? activeLabs.map(lab => <div className="planner-item" key={lab.id}>
              <span className="planner-check"><i className="bi bi-code-square" /></span>
              <span><strong>{lab.title}</strong><small>{lab.class_name} · {lab.concept} · {lab.duration_minutes} min</small>{lab.instructions && <small>{lab.instructions}</small>}</span>
              <textarea className="student-lab-response" aria-label={`Response for ${lab.title}`} value={labAnswers[lab.id] ?? ''} onChange={event => setLabAnswers(current => ({ ...current, [lab.id]: event.target.value }))} placeholder="Your response…" />
              <button className="primary mini" disabled={submittingLab !== null || !labAnswers[lab.id]?.trim()} onClick={() => void handleSubmitLab(lab.id)}>{submittingLab === lab.id ? 'Submitting…' : 'Submit'}</button>
            </div>) : <p>No active live labs are available.</p>}
            {labSubmitNotice && <p role="status">{labSubmitNotice}</p>}
            {labSubmitError && <p className="error" role="alert">{labSubmitError}</p>}
          </section>
          <div className="system-status"><span><i className="bi bi-circle-fill" /> Services</span><small>API {label(backend)} · DB {label(database)}</small></div>
        </aside>
      </div>
    </main>
  </div>
}
