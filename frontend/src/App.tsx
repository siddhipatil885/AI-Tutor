import { FormEvent, useEffect, useState } from 'react'
import { createAssignment, createClass, generateAssessment, getBackendHealth, getDatabaseHealth, getProjectCatalog, getProjectRecommendations, getTeacherDashboard, listClasses } from './services/api'
import { getCurrentUser, signIn, signOut, signUp } from './services/auth'

type View = 'home' | 'signin' | 'signup' | 'dashboard' | 'teacher'
type User = NonNullable<Awaited<ReturnType<typeof getCurrentUser>>>
type Status = 'checking' | 'connected' | 'unavailable'

const Logo = () => <div className="logo"><b>R</b><span>Re<span>:</span>Learn</span></div>
const routeFor = (view: View) => view === 'dashboard' ? '/dashboard' : view === 'teacher' ? '/teacher' : view === 'home' ? '/' : `/${view}`
const viewForPath = (path: string): View => path === '/dashboard' ? 'dashboard' : path === '/teacher' ? 'teacher' : path === '/signup' ? 'signup' : path === '/signin' ? 'signin' : 'home'

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

  if (loading) return <div className="auth-loading">Checking your session…</div>
  if (view === 'dashboard' && !user) return <div className="auth-loading">Redirecting to sign in…</div>
  if (view === 'teacher') return <TeacherDashboardView />
  if (view === 'home') return <Landing nav={navigate} />
  if (view === 'signin' || view === 'signup') return <Auth mode={view} nav={navigate} onAuthenticated={async () => { setUser(await getCurrentUser()); navigate('dashboard') }} />
  if (!user) return <div className="auth-loading">Redirecting to sign in…</div>
  return <Dashboard user={user} onLogout={async () => { await signOut(); setUser(null); navigate('signin') }} />
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

function Dashboard({ user, onLogout }: { user: User; onLogout: () => Promise<void> }) {
  const [backend, setBackend] = useState<Status>('checking')
  const [database, setDatabase] = useState<Status>('checking')
  useEffect(() => {
    getBackendHealth().then(result => setBackend(result.status === 'ok' ? 'connected' : 'unavailable')).catch(() => setBackend('unavailable'))
    getDatabaseHealth().then(result => setDatabase(result.status === 'ok' ? 'connected' : 'unavailable')).catch(() => setDatabase('unavailable'))
  }, [])
  const label = (status: Status) => status === 'checking' ? 'Checking…' : status === 'connected' ? 'Connected' : 'Unavailable'
  const firstName = (user.name || 'Learner').split(' ')[0]
  return <div className="app">
    <aside className="sidebar dashboard-sidebar">
      <Logo />
      <small>LEARNING SPACE</small>
      <button className="selected"><i className="bi bi-grid-1x2-fill" />Overview</button>
      <button><i className="bi bi-journal-code" />Practice</button>
      <button><i className="bi bi-bar-chart-line" />Progress</button>
      <button><i className="bi bi-bookmark" />Bookmarks</button>
      <div className="sidebar-divider" />
      <small>YOUR PLAN</small>
      <button><i className="bi bi-calendar3" />Daily planner</button>
      <button><i className="bi bi-bullseye" />Goals</button>
      <div className="profile">
        <b>{(user.name || user.email || 'U').slice(0, 2).toUpperCase()}</b>
        <span><strong>{user.name || 'Learner'}</strong><small>{user.email}</small></span>
        <button onClick={onLogout} aria-label="Log out"><i className="bi bi-box-arrow-right" /></button>
      </div>
    </aside>
    <main className="workspace dashboard-workspace">
      <header className="dashboard-header">
        <div><small>MONDAY, OCTOBER 6, 2025</small><h1>Long day, {firstName}?</h1><p>Let’s make a little progress today.</p></div>
        <div className="header-actions"><span className="streak"><i className="bi bi-fire" /> 4 day streak</span><button className="icon-button" aria-label="Notifications"><i className="bi bi-bell" /></button></div>
      </header>
      <div className="dashboard-grid">
        <section className="dashboard-main">
          <div className="plan-card">
            <div><small>TODAY'S PLAN</small><h2>Build your foundations</h2><p>Keep your momentum going with these focused sessions.</p></div>
            <div className="plan-progress"><strong>2 <span>/ 4</span></strong><small>completed</small><div><i style={{ width: '50%' }} /></div></div>
          </div>
          <div className="section-heading"><div><small>YOUR PROGRESS</small><h2>A little better every day.</h2></div><button className="text-button">View details <i className="bi bi-arrow-up-right" /></button></div>
          <div className="stats-grid">
            <div className="stat-card"><span className="stat-icon blue"><i className="bi bi-clock" /></span><small>LEARNING TIME</small><strong>3h 42m</strong><em><i className="bi bi-arrow-up" /> 18% this week</em></div>
            <div className="stat-card"><span className="stat-icon purple"><i className="bi bi-check2-circle" /></span><small>QUESTIONS SOLVED</small><strong>128</strong><em><i className="bi bi-arrow-up" /> 24 this week</em></div>
            <div className="stat-card"><span className="stat-icon orange"><i className="bi bi-lightning-charge" /></span><small>ACCURACY</small><strong>78%</strong><em><i className="bi bi-arrow-up" /> 6% this week</em></div>
          </div>
          <div className="chart-card"><div className="card-heading"><div><small>ACTIVITY</small><h3>Your learning rhythm</h3></div><span>Last 7 days <i className="bi bi-chevron-down" /></span></div><div className="activity-chart"><div className="chart-y"><span>60m</span><span>40m</span><span>20m</span><span>0m</span></div><div className="chart-bars">{[35, 58, 43, 78, 52, 88, 66].map((height, index) => <div className="bar-column" key={index}><div className="bar" style={{ height: `${height}%` }} /><small>{['M', 'T', 'W', 'T', 'F', 'S', 'S'][index]}</small></div>)}</div></div></div>
          <div className="section-heading topics-heading"><div><small>KEEP EXPLORING</small><h2>Popular topics</h2></div><button className="text-button">See all <i className="bi bi-arrow-right" /></button></div>
          <div className="topic-grid"><Topic icon="code-slash" title="Data Structures" meta="12 lessons" color="blue" /><Topic icon="braces" title="Algorithms" meta="8 lessons" color="purple" /><Topic icon="database" title="SQL Fundamentals" meta="10 lessons" color="orange" /></div>
        </section>
        <aside className="dashboard-rail">
          <div className="welcome-card"><span className="welcome-spark"><i className="bi bi-stars" /></span><small>YOUR NEXT STEP</small><h2>Understand the why, not just the how.</h2><p>Start a guided session to strengthen the concepts you’re working on.</p><button className="primary wide">Start a session <i className="bi bi-arrow-right" /></button></div>
          <div className="question-card"><div className="card-heading"><div><small>PROBLEM OF THE DAY</small><h3>Can you solve this?</h3></div><i className="bi bi-three-dots" /></div><span className="difficulty">MEDIUM</span><p>What is the time complexity of searching in a balanced binary search tree?</p><button className="outline-button">Try it now <i className="bi bi-arrow-up-right" /></button></div>
          <div className="planner-card"><div className="card-heading"><div><small>DAILY PLANNER</small><h3>Today's focus</h3></div><button className="icon-button"><i className="bi bi-plus-lg" /></button></div><PlannerItem title="Review arrays & strings" time="25 min" done /><PlannerItem title="Practice binary trees" time="30 min" /><PlannerItem title="Reflect on today's learning" time="10 min" /></div>
          <div className="system-status"><span><i className="bi bi-circle-fill" /> Services</span><small>API {label(backend)} · DB {label(database)}</small></div>
        </aside>
      </div>
    </main>
  </div>
}

function Topic({ icon, title, meta, color }: { icon: string; title: string; meta: string; color: string }) {
  return <button className="topic-card"><span className={`topic-icon ${color}`}><i className={`bi ${icon}`} /></span><span><strong>{title}</strong><small>{meta}</small></span><i className="bi bi-arrow-up-right topic-arrow" /></button>
}

function PlannerItem({ title, time, done = false }: { title: string; time: string; done?: boolean }) {
  return <div className={`planner-item ${done ? 'done' : ''}`}><span className="planner-check"><i className="bi bi-check" /></span><span><strong>{title}</strong><small>{time}</small></span></div>
}

function TeacherDashboardView() {
  const [dashboard, setDashboard] = useState<any>(null)
  const [projects, setProjects] = useState<any[]>([])
  const [classes, setClasses] = useState<any[]>([])
  const [title, setTitle] = useState('Loop Practice')
  const [language, setLanguage] = useState('python')
  const [difficulty, setDifficulty] = useState('beginner')
  const [questionCount, setQuestionCount] = useState(2)
  const [className, setClassName] = useState('Python Bootcamp')
  const [classDescription, setClassDescription] = useState('Starter cohort for loop and condition practice')
  const [status, setStatus] = useState('')
  const [loading, setLoading] = useState(false)

  const teacherId = 1

  const refresh = async () => {
    try {
      const dashboardResponse = await getTeacherDashboard()
      setDashboard(dashboardResponse)
      const classesResponse = await listClasses(teacherId)
      setClasses(classesResponse)
      const projectResponse = await getProjectCatalog(language)
      setProjects(projectResponse.projects)
    } catch {
      setDashboard(null)
      setClasses([])
      setProjects([])
    }
  }

  useEffect(() => {
    void refresh()
  }, [])

  const handleCreateClass = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setLoading(true)
    try {
      await createClass({ teacher_id: teacherId, name: className, language, description: classDescription })
      setStatus('Class created successfully.')
      setClassName('')
      setClassDescription('')
      await refresh()
    } catch {
      setStatus('Unable to create the class right now.')
    } finally {
      setLoading(false)
    }
  }

  const handleCreateAssignment = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const selectedClass = classes[0]
    if (!selectedClass) {
      setStatus('Create a class before creating an assignment.')
      return
    }
    setLoading(true)
    try {
      await createAssignment({
        class_id: selectedClass.id,
        teacher_id: teacherId,
        title,
        language,
        difficulty,
        question_count: questionCount,
        question_types: ['mcq', 'output_prediction'],
      })
      setStatus('Assignment saved as a draft.')
      setTitle('')
    } catch {
      setStatus('Unable to save the assignment.')
    } finally {
      setLoading(false)
    }
  }

  const assignment = dashboard ? { total: dashboard.total_students, score: dashboard.average_mastery * 100 } : { total: 0, score: 0 }

  return <div className="teacher-shell">
    <style>{`
      .teacher-shell { padding: 32px; background: #10141b; min-height: 100vh; }
      .teacher-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
      .teacher-header h1 { margin: 8px 0 0; font-size: 2.2rem; }
      .teacher-header small { color: #8ab6ff; letter-spacing: 0.12em; font-size: 0.7rem; }
      .teacher-metrics { display: grid; grid-template-columns: repeat(3, minmax(170px, 1fr)); gap: 16px; margin-bottom: 22px; }
      .metric-card, .panel, .class-form, .assignment-form { background: #151b25; border: 1px solid #2a3545; border-radius: 14px; padding: 18px 20px; }
      .metric-card span { display: block; color: #8ca0bc; font-size: 0.74rem; letter-spacing: .08em; text-transform: uppercase; }
      .metric-card strong { display: block; margin-top: 10px; font-size: 2rem; }
      .teacher-panels { display: grid; grid-template-columns: repeat(2, minmax(260px, 1fr)); gap: 18px; margin-bottom: 18px; }
      .panel h3, .class-form h3, .assignment-form h3 { margin: 0 0 14px; font-size: 1.12rem; }
      .topic-row, .project-row, .risk-row { display: flex; justify-content: space-between; align-items: center; gap: 12px; padding: 12px 0; border-top: 1px solid #2d3848; }
      .topic-row:first-child, .project-row:first-child, .risk-row:first-child { border-top: 0; }
      .topic-row strong, .project-row strong, .risk-row strong { display: block; }
      .topic-row span, .project-row span, .risk-row span { display: block; color: #9aa9bf; font-size: 0.85rem; }
      .project-row small { color: #89a7ff; }
      .teacher-form-grid { display: grid; grid-template-columns: repeat(2, minmax(260px, 1fr)); gap: 18px; margin-top: 18px; }
      .class-form, .assignment-form { display: flex; flex-direction: column; gap: 12px; }
      .class-form input, .class-form textarea, .assignment-form input, .assignment-form select { width: 100%; border: 1px solid #303b4d; background: #0d1117; color: #eaf1ff; border-radius: 10px; padding: 10px 12px; }
      .class-form textarea { min-height: 74px; resize: vertical; }
      .teaching-actions { display: flex; gap: 10px; flex-wrap: wrap; }
      .status-box { margin-top: 12px; color: #9be7c1; font-size: 0.9rem; }
    `}</style>
    <header className="teacher-header">
      <div>
        <small>TEACHER DASHBOARD</small>
        <h1>Class overview</h1>
      </div>
      <button className="primary mini">Create assessment</button>
    </header>

    <div className="teacher-metrics">
      <div className="metric-card"><span>Total students</span><strong>{assignment.total}</strong></div>
      <div className="metric-card"><span>Avg. mastery</span><strong>{assignment.score.toFixed(0)}%</strong></div>
      <div className="metric-card"><span>At risk</span><strong>{dashboard?.at_risk_students?.length ?? 0}</strong></div>
    </div>

    <div className="teacher-panels">
      <section className="panel">
        <h3>Weak topics</h3>
        {(dashboard?.weak_topics ?? [{ topic: 'loop boundaries', mastery: 0.72, weak_students: ['Current class'] }]).map((item: any) => (
          <div className="topic-row" key={item.topic}> 
            <div>
              <strong>{item.topic}</strong>
              <span>{item.weak_students.join(', ') || 'Needs attention'}</span>
            </div>
            <b>{(item.mastery * 100).toFixed(0)}%</b>
          </div>
        ))}
      </section>

      <section className="panel">
        <h3>Project recommendations</h3>
        {(projects.length ? projects : [{ title: 'Python Quiz Game', difficulty: 'beginner', description: 'Loop-based project recommendation for weak concept repair.', focus: ['C001'] }]).map((project: any) => (
          <div className="project-row" key={project.title}>
            <div>
              <strong>{project.title}</strong>
              <span>{project.description}</span>
            </div>
            <small>{project.difficulty}</small>
          </div>
        ))}
      </section>
    </div>

    <div className="teacher-form-grid">
      <form className="class-form" onSubmit={handleCreateClass}>
        <h3>Create class</h3>
        <input value={className} onChange={(event) => setClassName(event.target.value)} placeholder="Class name" required />
        <select value={language} onChange={(event) => setLanguage(event.target.value)}>
          <option value="python">Python</option>
          <option value="c">C</option>
          <option value="cpp">C++</option>
          <option value="html">HTML</option>
        </select>
        <textarea value={classDescription} onChange={(event) => setClassDescription(event.target.value)} placeholder="Short description" />
        <div className="teaching-actions">
          <button type="submit" className="primary mini" disabled={loading}>{loading ? 'Saving…' : 'Create class'}</button>
        </div>
      </form>

      <form className="assignment-form" onSubmit={handleCreateAssignment}>
        <h3>Create assignment</h3>
        <input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Assignment title" required />
        <select value={difficulty} onChange={(event) => setDifficulty(event.target.value)}>
          <option value="beginner">Beginner</option>
          <option value="intermediate">Intermediate</option>
          <option value="advanced">Advanced</option>
        </select>
        <select value={language} onChange={(event) => setLanguage(event.target.value)}>
          <option value="python">Python</option>
          <option value="c">C</option>
          <option value="cpp">C++</option>
          <option value="html">HTML</option>
        </select>
        <input type="number" min={1} max={10} value={questionCount} onChange={(event) => setQuestionCount(Number(event.target.value) || 1)} />
        <div className="teaching-actions">
          <button type="submit" className="primary mini" disabled={loading}>{loading ? 'Saving…' : 'Create assignment'}</button>
        </div>
      </form>
    </div>

    <section className="panel risk-panel" style={{ marginTop: 18 }}>
      <h3>At-risk students</h3>
      {(dashboard?.at_risk_students ?? [{ student: 'Nikhil', reasons: ['multiple active misconceptions'] }]).map((entry: any) => (
        <div className="risk-row" key={entry.student}>
          <strong>{entry.student}</strong>
          <span>{entry.reasons.join(', ')}</span>
        </div>
      ))}
    </section>

    {status && <div className="status-box">{status}</div>}
  </div>
}

function Connection({ name, status }: { name: string; status: string }) {
  return <div className="connection-row"><span><i className={`bi bi-${status === 'Connected' ? 'check-circle-fill' : status === 'Checking…' ? 'arrow-repeat' : 'exclamation-circle-fill'}`} /> {name}</span><strong>{status}</strong></div>
}
