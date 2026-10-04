import { FormEvent, useEffect, useRef, useState } from 'react'
import {
  createAssignment,
  createClass,
  createLab,
  generateAssessment,
  getAssignmentReviews,
  getClassAssignments,
  getProjectCatalog,
  getProjectRecommendations,
  getTeacherDashboard,
  listClasses,
  listLabs,
  publishAssignment,
  updateLabStatus,
} from './services/api'
import { getCurrentUser } from './services/auth'

type PageKey = 'overview' | 'classes' | 'assignments' | 'labs' | 'analytics' | 'projects'
type TeacherClass = Awaited<ReturnType<typeof listClasses>>[number]
type TeacherAssignment = Awaited<ReturnType<typeof getClassAssignments>>[number] & { class_name: string }
type TeacherLab = Awaited<ReturnType<typeof listLabs>>[number] & { class_name: string }
type DashboardData = Awaited<ReturnType<typeof getTeacherDashboard>>
type Project = Awaited<ReturnType<typeof getProjectCatalog>>['projects'][number]
type AssignmentReview = Awaited<ReturnType<typeof getAssignmentReviews>>[number]
type TeacherUser = NonNullable<Awaited<ReturnType<typeof getCurrentUser>>>

const conceptForTopic: Record<string, string> = {
  'loop boundaries': 'C001',
  conditionals: 'C002',
  functions: 'C003',
  lists: 'C004',
}
const navigation: Array<{ key: PageKey; label: string; icon: string; path: string }> = [
  { key: 'overview', label: 'Overview', icon: 'bi-grid-1x2', path: '/teacher' },
  { key: 'classes', label: 'My Classes', icon: 'bi-people', path: '/teacher/classes' },
  { key: 'assignments', label: 'Assignments', icon: 'bi-journal-check', path: '/teacher/assignments' },
  { key: 'labs', label: 'Live Labs', icon: 'bi-code-square', path: '/teacher/labs' },
  { key: 'analytics', label: 'Analytics', icon: 'bi-bar-chart', path: '/teacher/analytics' },
  { key: 'projects', label: 'Projects', icon: 'bi-lightbulb', path: '/teacher/projects' },
]

const pageFromPath = (path: string): PageKey => navigation.find((item) => item.path === path)?.key ?? 'overview'
const labelForPage = (page: PageKey) => navigation.find((item) => item.key === page)?.label ?? 'Overview'

export default function TeacherDashboard({ user, onLogout, onInstitution }: { user: TeacherUser; onLogout: () => Promise<void>; onInstitution: () => void }) {
  const teacherId = user.id
  const [page, setPage] = useState<PageKey>(() => pageFromPath(window.location.pathname))
  const [collapsed, setCollapsed] = useState(false)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [dashboard, setDashboard] = useState<DashboardData | null>(null)
  const [classes, setClasses] = useState<TeacherClass[]>([])
  const [assignments, setAssignments] = useState<TeacherAssignment[]>([])
  const [labs, setLabs] = useState<TeacherLab[]>([])
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState('')
  const [notice, setNotice] = useState('')
  const [refreshKey, setRefreshKey] = useState(0)
  const [language, setLanguage] = useState('python')

  useEffect(() => {
    const syncRoute = () => setPage(pageFromPath(window.location.pathname))
    window.addEventListener('popstate', syncRoute)
    return () => window.removeEventListener('popstate', syncRoute)
  }, [])

  useEffect(() => {
    let current = true
    setLoading(true)
    setLoadError('')
    Promise.all([getTeacherDashboard(), listClasses(teacherId)])
      .then(async ([dashboardData, classList]) => {
        const classData = await Promise.all(classList.map(async (classItem) => {
          const [classLabs, classAssignments] = await Promise.all([
            listLabs(classItem.id).catch(() => []),
            getClassAssignments(classItem.id).catch(() => []),
          ])
          return {
            labs: classLabs.map((lab) => ({ ...lab, class_name: classItem.name })),
            assignments: classAssignments.map((assignment) => ({ ...assignment, class_name: classItem.name })),
          }
        }))
        const recommendations = await getProjectRecommendations({
          language,
          mastery: Object.fromEntries((dashboardData.weak_topics ?? []).flatMap((topic) => {
            const conceptId = conceptForTopic[topic.topic.toLowerCase()]
            return conceptId ? [[conceptId, topic.mastery]] : []
          })),
        }).catch(() => null)
        const catalog = recommendations ?? (await getProjectCatalog(language)).projects
        if (!current) return
        setDashboard(dashboardData)
        setClasses(classList)
        setLabs(classData.flatMap((item) => item.labs))
        setAssignments(classData.flatMap((item) => item.assignments))
        setProjects(catalog)
      })
      .catch(() => {
        if (!current) return
        setLoadError('Teacher data could not be loaded. Check the API connection and try again.')
        setDashboard(null)
        setClasses([])
        setLabs([])
        setAssignments([])
        setProjects([])
      })
      .finally(() => { if (current) setLoading(false) })
    return () => { current = false }
  }, [refreshKey, language, teacherId])

  const navigate = (nextPage: PageKey) => {
    const destination = navigation.find((item) => item.key === nextPage)?.path ?? '/teacher'
    if (window.location.pathname !== destination) window.history.pushState({}, '', destination)
    setPage(nextPage)
    setDrawerOpen(false)
    setNotice('')
  }
  const refresh = () => setRefreshKey((key) => key + 1)
  const activeItem = navigation.find((item) => item.key === page) ?? navigation[0]

  return <div className={`teacher-app ${collapsed ? 'is-collapsed' : ''}`}>
    {drawerOpen && <button className="teacher-drawer-backdrop" aria-label="Close navigation" onClick={() => setDrawerOpen(false)} />}
    <aside className={`teacher-sidebar ${drawerOpen ? 'drawer-open' : ''}`}>
      <div className="teacher-brand"><b>R</b><span>Re<span>:</span>Learn</span></div>
      <small className="teacher-nav-label">TEACHING SPACE</small>
      <nav aria-label="Teacher navigation">
        {navigation.map((item) => <button key={item.key} className={page === item.key ? 'active' : ''} title={collapsed ? item.label : undefined} onClick={() => navigate(item.key)}>
          <i className={`bi ${item.icon}`} /><span>{item.label}</span>
        </button>)}
        <button className="teacher-institution-link" onClick={onInstitution} title={collapsed ? 'Institution' : undefined}><i className="bi bi-buildings" /><span>Institution</span></button>
      </nav>
      <div className="teacher-sidebar-bottom">
        <div className="teacher-profile-avatar">{(user.name || user.email || 'T').slice(0, 1).toUpperCase()}</div>
        <div className="teacher-profile-copy"><strong>{user.name || 'Teacher'}</strong><small>Teacher account</small></div>
        <button className="teacher-logout" onClick={() => void onLogout()} aria-label="Log out" title="Log out"><i className="bi bi-box-arrow-right" /></button>
      </div>
    </aside>
    <div className="teacher-content">
      <header className="teacher-topbar">
        <div className="teacher-topbar-title">
          <button className="teacher-menu-button" onClick={() => setDrawerOpen(true)} aria-label="Open navigation"><i className="bi bi-list" /></button>
          <button className="teacher-collapse-button" onClick={() => setCollapsed((value) => !value)} aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'} title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}><i className={`bi ${collapsed ? 'bi-layout-sidebar' : 'bi-layout-sidebar-inset'}`} /></button>
          <div><small>TEACHER WORKSPACE</small><h1>{activeItem.label}</h1></div>
        </div>
        <div className="teacher-topbar-actions"><span className="teacher-user-name">{user.name || user.email}</span><button className="teacher-top-logout" onClick={() => void onLogout()}><i className="bi bi-box-arrow-right" /> Log out</button></div>
      </header>
      <main className="teacher-page">
        {notice && <div className="teacher-notice" role="status">{notice}</div>}
        {loadError && <div className="teacher-load-error" role="alert">{loadError}<button className="outline-button mini" onClick={refresh}>Retry</button></div>}
        {loading ? <div className="teacher-empty">Loading teacher workspace…</div> : <>
          {page === 'overview' && <Overview dashboard={dashboard} labs={labs} assignments={assignments} onNavigate={navigate} />}
          {page === 'classes' && <ClassesPage teacherId={teacherId} classes={classes} labs={labs} assignments={assignments} language={language} setLanguage={setLanguage} onCreated={(message) => { setNotice(message); refresh() }} />}
          {page === 'assignments' && <AssignmentsPage teacherId={teacherId} classes={classes} assignments={assignments} language={language} setLanguage={setLanguage} onCreated={(message) => { setNotice(message); refresh() }} />}
          {page === 'labs' && <LabsPage teacherId={teacherId} classes={classes} labs={labs} language={language} setLanguage={setLanguage} onChanged={(message) => { setNotice(message); refresh() }} />}
          {page === 'analytics' && <AnalyticsPage dashboard={dashboard} />}
          {page === 'projects' && <ProjectsPage projects={projects} language={language} setLanguage={setLanguage} />}
        </>}
      </main>
    </div>
  </div>
}

function Overview({ dashboard, labs, assignments, onNavigate }: { dashboard: DashboardData | null; labs: TeacherLab[]; assignments: TeacherAssignment[]; onNavigate: (page: PageKey) => void }) {
  const activeLabs = labs.filter((lab) => lab.status === 'active').length
  const metrics = [
    { label: 'Total students', value: dashboard ? String(dashboard.total_students) : '—', icon: 'bi-people', tone: 'blue' },
    { label: 'Average mastery', value: dashboard?.average_mastery != null ? `${Math.round(dashboard.average_mastery * 100)}%` : '—', icon: 'bi-bullseye', tone: 'yellow' },
    { label: 'Active labs', value: String(activeLabs), icon: 'bi-broadcast', tone: 'mint' },
    { label: 'At-risk students', value: dashboard ? String(dashboard.at_risk_students.length) : '—', icon: 'bi-exclamation-triangle', tone: 'coral' },
  ]
  return <>
    <div className="teacher-page-heading"><div><small>CLASSROOM SNAPSHOT</small><h2>See where learning stands.</h2><p>Summary values use enrolled learners and recorded learner profiles.</p></div></div>
    <section className="teacher-metric-grid" aria-label="Classroom summary">
      {metrics.map((metric) => <article className="teacher-metric" key={metric.label}><span className={`teacher-metric-icon ${metric.tone}`}><i className={`bi ${metric.icon}`} /></span><small>{metric.label}</small><strong>{metric.value}</strong></article>)}
    </section>
    <section className="teacher-overview-grid">
      <article className="teacher-panel teacher-performance"><div className="teacher-panel-heading"><div><small>PERFORMANCE</small><h3>Mastery by topic</h3></div><button className="text-button" onClick={() => onNavigate('analytics')}>Open analytics <i className="bi bi-arrow-up-right" /></button></div>
        {dashboard?.weak_topics.length ? <div className="teacher-topic-bars">{dashboard.weak_topics.map((topic) => <div className="teacher-topic-bar" key={topic.topic}><div><strong>{topic.topic}</strong><b>{Math.round(topic.mastery * 100)}%</b></div><span><i style={{ width: `${Math.max(0, Math.min(100, topic.mastery * 100))}%` }} /></span></div>)}</div> : <EmptyState text="No topic performance data is available yet." />}
      </article>
      <article className="teacher-panel"><div className="teacher-panel-heading"><div><small>NEEDS ATTENTION</small><h3>Signals to review</h3></div></div>
        {dashboard?.at_risk_students.length ? <div className="teacher-insight-list">{dashboard.at_risk_students.slice(0, 4).map((student) => <div className="teacher-insight" key={student.student}><i className="bi bi-person-exclamation" /><div><strong>{student.student}</strong><span>{student.reasons.join(', ') || 'Below class baseline'}</span></div><small>{Math.round(student.risk_score * 100)}%</small></div>)}</div> : <EmptyState text="No at-risk learner signals are reported." />}
        <p className="teacher-data-note">Risk signals use available learner profiles and confirmed active misconceptions. Empty or untracked values are not estimated.</p>
      </article>
    </section>
    <section className="teacher-quick-actions"><div><small>QUICK ACTIONS</small><h3>What would you like to do?</h3></div><div className="teacher-action-buttons"><button className="primary mini" onClick={() => onNavigate('classes')}><i className="bi bi-plus-lg" /> Create class</button><button className="outline-button mini" onClick={() => onNavigate('assignments')}><i className="bi bi-journal-plus" /> Create assignment</button><button className="outline-button mini" onClick={() => onNavigate('labs')}><i className="bi bi-play-circle" /> Start a live lab</button><button className="outline-button mini" onClick={() => { window.history.pushState({}, '', '/journey'); window.dispatchEvent(new PopStateEvent('popstate')) }}><i className="bi bi-person-video3" /> Test student journey</button></div></section>
    <div className="teacher-overview-footer"><span>{assignments.length} assignments across your classes</span><span>{labs.length} live labs across your classes</span></div>
  </>
}

function ClassesPage({ teacherId, classes, labs, assignments, language, setLanguage, onCreated }: { teacherId: number; classes: TeacherClass[]; labs: TeacherLab[]; assignments: TeacherAssignment[]; language: string; setLanguage: (value: string) => void; onCreated: (message: string) => void }) {
  const [formOpen, setFormOpen] = useState(false)
  const [selectedClassId, setSelectedClassId] = useState<number | null>(null)
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const busyGuard = useRef(false)
  const selectedClass = classes.find((item) => item.id === selectedClassId)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (busyGuard.current) return
    if (classes.some((item) => item.name.trim().toLowerCase() === name.trim().toLowerCase())) {
      setError('A class with this name already exists in your list.')
      return
    }
    busyGuard.current = true
    setBusy(true)
    setError('')
    try {
      await createClass({ teacher_id: teacherId, name: name.trim(), language, description: description.trim() })
      setName('')
      setDescription('')
      setFormOpen(false)
      onCreated('Class created successfully.')
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Unable to create this class.')
    } finally {
      busyGuard.current = false
      setBusy(false)
    }
  }

  return <>
    <div className="teacher-page-heading teacher-heading-action"><div><small>YOUR TEACHING GROUPS</small><h2>My classes</h2><p>Organize cohorts and open a class to review its current work.</p></div><button className="primary mini" onClick={() => setFormOpen((value) => !value)}><i className="bi bi-plus-lg" /> {formOpen ? 'Close form' : 'Create class'}</button></div>
    {formOpen && <form className="teacher-form-panel" onSubmit={submit}><div className="teacher-form-heading"><h3>New class</h3><p>Class creation is saved to your teacher workspace.</p></div><label>Class name<input value={name} onChange={(event) => setName(event.target.value)} required maxLength={100} placeholder="e.g. Python foundations" /></label><label>Programming language<select value={language} onChange={(event) => setLanguage(event.target.value)}><LanguageOptions /></select></label><label>Description<textarea value={description} onChange={(event) => setDescription(event.target.value)} maxLength={500} placeholder="What will this class focus on?" /></label>{error && <p className="teacher-form-error">{error}</p>}<button className="primary mini" disabled={busy}>{busy ? 'Creating…' : 'Create class'}</button></form>}
    {classes.length ? <div className="teacher-class-grid">{classes.map((item) => <button className={`teacher-class-card ${selectedClassId === item.id ? 'selected' : ''}`} key={item.id} onClick={() => setSelectedClassId(selectedClassId === item.id ? null : item.id)}><span className="teacher-class-language">{item.language.toUpperCase()}</span><h3>{item.name}</h3><p>{item.description || 'No class description provided.'}</p><div><span><i className="bi bi-journal-check" /> {assignments.filter((entry) => entry.class_id === item.id).length} assignments</span><span><i className="bi bi-code-square" /> {labs.filter((entry) => entry.class_id === item.id).length} labs</span></div><small>Roster count and per-class performance are not available from the current API.</small></button>)}</div> : <EmptyState text="No classes yet. Create a class to get started." />}
    {selectedClass && <section className="teacher-panel teacher-class-detail"><div className="teacher-panel-heading"><div><small>CLASS DETAILS</small><h3>{selectedClass.name}</h3></div><button className="text-button" onClick={() => setSelectedClassId(null)}>Close</button></div><p>{selectedClass.description || 'No class description provided.'} · {selectedClass.language}</p><div className="teacher-detail-columns"><div><strong>Assignments</strong>{assignments.filter((item) => item.class_id === selectedClass.id).map((item) => <p key={item.id}>{item.title} · {item.status}</p>)}{!assignments.some((item) => item.class_id === selectedClass.id) && <small>No assignments in this class.</small>}</div><div><strong>Labs</strong>{labs.filter((item) => item.class_id === selectedClass.id).map((item) => <p key={item.id}>{item.title} · {item.status}</p>)}{!labs.some((item) => item.class_id === selectedClass.id) && <small>No labs in this class.</small>}</div></div></section>}
  </>
}

function AssignmentsPage({ teacherId, classes, assignments, language, setLanguage, onCreated }: { teacherId: number; classes: TeacherClass[]; assignments: TeacherAssignment[]; language: string; setLanguage: (value: string) => void; onCreated: (message: string) => void }) {
  const [formOpen, setFormOpen] = useState(false)
  const [selectedClass, setSelectedClass] = useState('')
  const [title, setTitle] = useState('')
  const [difficulty, setDifficulty] = useState('beginner')
  const [questionCount, setQuestionCount] = useState(3)
  const [topics, setTopics] = useState('loop boundaries')
  const [generated, setGenerated] = useState<Awaited<ReturnType<typeof generateAssessment>> | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [actionBusy, setActionBusy] = useState<number | null>(null)
  const [assignmentReviews, setAssignmentReviews] = useState<Record<number, AssignmentReview[]>>({})
  const busyGuard = useRef(false)

  async function publishDraft(assignmentId: number) {
    setActionBusy(assignmentId)
    setError('')
    try {
      await publishAssignment(assignmentId)
      onCreated('Assignment published for enrolled students.')
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Unable to publish this assignment.')
    } finally { setActionBusy(null) }
  }

  async function toggleReviews(assignmentId: number) {
    if (Object.hasOwn(assignmentReviews, assignmentId)) {
      setAssignmentReviews(current => {
        const next = { ...current }
        delete next[assignmentId]
        return next
      })
      return
    }
    setActionBusy(assignmentId)
    setError('')
    try {
      const reviews = await getAssignmentReviews(assignmentId)
      setAssignmentReviews(current => ({ ...current, [assignmentId]: reviews }))
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Unable to load student attempts.')
    } finally { setActionBusy(null) }
  }

  async function generateDraft() {
    setBusy(true)
    setError('')
    try {
      setGenerated(await generateAssessment({ language, topics: topics.split(',').map((topic) => topic.trim()).filter(Boolean), difficulty, question_count: questionCount, question_types: ['mcq', 'output_prediction'] }))
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Unable to generate an assignment preview.')
    } finally { setBusy(false) }
  }
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (busyGuard.current) return
    const classId = Number(selectedClass)
    if (!classId) { setError('Choose a class before saving this assignment.'); return }
    busyGuard.current = true
    setBusy(true)
    setError('')
    try {
      await createAssignment({ class_id: classId, teacher_id: teacherId, title: title.trim(), language, difficulty, question_count: questionCount, question_types: ['mcq', 'output_prediction'] })
      setTitle('')
      setGenerated(null)
      setFormOpen(false)
      onCreated('Assignment saved as a draft.')
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Unable to save this assignment.')
    } finally { busyGuard.current = false; setBusy(false) }
  }

  return <>
    <div className="teacher-page-heading teacher-heading-action"><div><small>CLASS WORK</small><h2>Assignments</h2><p>Review saved assignments and create new drafts.</p></div><button className="primary mini" onClick={() => setFormOpen((value) => !value)}><i className="bi bi-plus-lg" /> {formOpen ? 'Close form' : 'Create assignment'}</button></div>
    {formOpen && <form className="teacher-form-panel" onSubmit={submit}><div className="teacher-form-heading"><h3>Assignment draft</h3><p>Generation creates a preview. Saving uses the existing assignment API and stores its generated question set as a draft.</p></div><div className="teacher-form-grid-inner"><label>Assignment title<input value={title} onChange={(event) => setTitle(event.target.value)} required maxLength={120} placeholder="Loop practice" /></label><label>Class<select required value={selectedClass} onChange={(event) => setSelectedClass(event.target.value)}><option value="">Choose a class</option>{classes.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label><label>Language<select value={language} onChange={(event) => setLanguage(event.target.value)}><LanguageOptions /></select></label><label>Difficulty<select value={difficulty} onChange={(event) => setDifficulty(event.target.value)}><option value="beginner">Beginner</option><option value="intermediate">Intermediate</option><option value="advanced">Advanced</option></select></label><label>Question count<input type="number" min={1} max={10} value={questionCount} onChange={(event) => setQuestionCount(Math.max(1, Math.min(10, Number(event.target.value) || 1)))} /></label><label>Topics for preview<input value={topics} onChange={(event) => setTopics(event.target.value)} placeholder="Comma-separated topics" /></label></div>{error && <p className="teacher-form-error">{error}</p>}<div className="teacher-action-buttons"><button type="button" className="outline-button mini" disabled={busy} onClick={() => void generateDraft()}><i className="bi bi-stars" /> {busy ? 'Working…' : 'Generate preview'}</button><button className="primary mini" disabled={busy || !classes.length}>{busy ? 'Saving…' : 'Save as draft'}</button></div>
      {!classes.length && <p className="teacher-form-error">Create a class before saving assignments.</p>}
      {generated && <div className="teacher-generated-preview"><h4>Generated preview · {generated.questions.length} questions</h4>{generated.questions.map((question) => <article key={question.id}><small>{question.topic} · {question.question_type}</small><p>{question.prompt}</p></article>)}<p className="teacher-data-note">Questions cannot be edited yet. Save as a draft, then publish it from the assignment library.</p></div>}
    </form>}
    {error && !formOpen && <p className="teacher-form-error" role="alert">{error}</p>}
    <section className="teacher-panel teacher-table-panel"><div className="teacher-panel-heading"><div><small>ASSIGNMENT LIBRARY</small><h3>{assignments.length} saved assignments</h3></div></div>{assignments.length ? <div className="teacher-table-wrap"><table className="teacher-table"><thead><tr><th>Assignment</th><th>Class</th><th>Questions</th><th>Difficulty</th><th>Status</th><th>Dates</th></tr></thead><tbody>{assignments.map((item) => <tr key={item.id}><td><strong>{item.title}</strong></td><td>{item.class_name}</td><td>{item.question_count}</td><td>{item.difficulty}</td><td><span className={`teacher-status status-${item.status}`}>{item.status}</span></td><td>Not provided</td></tr>)}</tbody></table></div> : <EmptyState text="No assignments have been created yet." />}
      {assignments.map(item => <article className="teacher-lab-row" key={`actions-${item.id}`}><div className="teacher-lab-copy"><strong>{item.title}</strong><span>{item.class_name} · {item.status}</span></div><div className="teacher-lab-actions">{item.status === 'draft' && <button className="primary mini" disabled={actionBusy !== null} onClick={() => void publishDraft(item.id)}>{actionBusy === item.id ? 'Working…' : 'Publish'}</button>}<button className="outline-button mini" disabled={actionBusy !== null} onClick={() => void toggleReviews(item.id)}>{actionBusy === item.id ? 'Loading…' : Object.hasOwn(assignmentReviews, item.id) ? 'Hide attempts' : 'Review attempts'}</button></div>{Object.hasOwn(assignmentReviews, item.id) && <div className="teacher-assignment-reviews">{assignmentReviews[item.id].length ? assignmentReviews[item.id].map(attempt => <div key={attempt.id}><strong>{attempt.student_name}</strong><span>Attempt {attempt.attempt_number} · {Math.round(attempt.score)}%</span><small>{attempt.feedback.map(result => `${result.question_id}: ${result.is_correct ? 'correct' : 'incorrect'}`).join(' · ')}</small></div>) : <p>No student attempts have been submitted.</p>}</div>}</article>)}
    </section>
  </>
}

function LabsPage({ teacherId, classes, labs, language, setLanguage, onChanged }: { teacherId: number; classes: TeacherClass[]; labs: TeacherLab[]; language: string; setLanguage: (value: string) => void; onChanged: (message: string) => void }) {
  const [formOpen, setFormOpen] = useState(false)
  const [classId, setClassId] = useState('')
  const [title, setTitle] = useState('')
  const [concept, setConcept] = useState('loop boundaries')
  const [difficulty, setDifficulty] = useState('beginner')
  const [duration, setDuration] = useState(30)
  const [busy, setBusy] = useState(false)
  const [busyLab, setBusyLab] = useState<number | null>(null)
  const [error, setError] = useState('')
  const busyGuard = useRef(false)
  const activeLabs = labs.filter((lab) => ['active', 'scheduled', 'paused'].includes(lab.status))
  const recentLabs = labs.filter((lab) => !['active', 'scheduled', 'paused'].includes(lab.status))

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (busyGuard.current) return
    const selected = classes.find((item) => item.id === Number(classId))
    if (!selected) { setError('Choose a class before creating a lab.'); return }
    busyGuard.current = true
    setBusy(true)
    setError('')
    try {
      await createLab(selected.id, { teacher_id: teacherId, title: title.trim(), language, concept, difficulty, instructions: `Practice ${concept} in ${language}.`, duration_minutes: duration })
      setTitle('')
      setFormOpen(false)
      onChanged('Lab created as a draft. Start it from the active lab list when ready.')
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Unable to create this lab.')
    } finally { busyGuard.current = false; setBusy(false) }
  }
  async function changeStatus(lab: TeacherLab, nextStatus: string) {
    setBusyLab(lab.id)
    setError('')
    try { await updateLabStatus(lab.id, nextStatus); onChanged(`Lab ${nextStatus === 'active' ? 'started' : nextStatus === 'paused' ? 'paused' : 'completed'}.`) }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Unable to update this lab.') }
    finally { setBusyLab(null) }
  }

  return <>
    <div className="teacher-page-heading teacher-heading-action"><div><small>CLASSROOM SESSIONS</small><h2>Live labs</h2><p>Start, pause, resume, and complete hands-on class sessions.</p></div><button className="primary mini" onClick={() => setFormOpen((value) => !value)}><i className="bi bi-plus-lg" /> {formOpen ? 'Close form' : 'Create live lab'}</button></div>
    {formOpen && <form className="teacher-form-panel" onSubmit={submit}><div className="teacher-form-heading"><h3>New live lab</h3><p>New labs begin in draft status.</p></div><div className="teacher-form-grid-inner"><label>Lab title<input value={title} onChange={(event) => setTitle(event.target.value)} required maxLength={120} placeholder="Loops warm-up" /></label><label>Class<select required value={classId} onChange={(event) => setClassId(event.target.value)}><option value="">Choose a class</option>{classes.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label><label>Language<select value={language} onChange={(event) => setLanguage(event.target.value)}><LanguageOptions /></select></label><label>Topic<select value={concept} onChange={(event) => setConcept(event.target.value)}><option value="loop boundaries">Loop boundaries</option><option value="conditionals">Conditionals</option><option value="functions">Functions</option><option value="general">General review</option></select></label><label>Difficulty<select value={difficulty} onChange={(event) => setDifficulty(event.target.value)}><option value="beginner">Beginner</option><option value="intermediate">Intermediate</option><option value="advanced">Advanced</option></select></label><label>Duration in minutes<input type="number" min={15} max={120} value={duration} onChange={(event) => setDuration(Math.max(15, Math.min(120, Number(event.target.value) || 30)))} /></label></div>{error && <p className="teacher-form-error">{error}</p>}<button className="primary mini" disabled={busy || !classes.length}>{busy ? 'Creating…' : 'Create lab'}</button>{!classes.length && <p className="teacher-form-error">Create a class before creating a live lab.</p>}</form>}
    {error && !formOpen && <p className="teacher-form-error">{error}</p>}
    <section className="teacher-panel teacher-labs-panel"><div className="teacher-panel-heading"><div><small>IN SESSION</small><h3>Active and paused</h3></div></div>{activeLabs.length ? <div className="teacher-lab-list">{activeLabs.map((lab) => <LabRow key={lab.id} lab={lab} busy={busyLab === lab.id} onStatus={changeStatus} />)}</div> : <EmptyState text="No active labs. Start a draft from the recent labs list." />}</section>
    <section className="teacher-panel teacher-labs-panel"><div className="teacher-panel-heading"><div><small>LAB LIBRARY</small><h3>Drafts and completed</h3></div></div>{recentLabs.length ? <div className="teacher-lab-list">{recentLabs.map((lab) => <LabRow key={lab.id} lab={lab} busy={busyLab === lab.id} onStatus={changeStatus} />)}</div> : <EmptyState text="No recent labs yet." />}</section>
  </>
}

function LabRow({ lab, busy, onStatus }: { lab: TeacherLab; busy: boolean; onStatus: (lab: TeacherLab, status: string) => void }) {
  const actions = lab.status === 'completed' || lab.status === 'archived' ? [] : lab.status === 'active' ? [['paused', 'Pause'], ['completed', 'Complete']] : lab.status === 'paused' ? [['active', 'Resume'], ['completed', 'Complete']] : [['active', 'Start']]
  return <article className="teacher-lab-row"><div className="teacher-lab-mark"><i className="bi bi-code-slash" /></div><div className="teacher-lab-copy"><strong>{lab.title}</strong><span>{lab.class_name} · {lab.concept} · {lab.duration_minutes} min</span></div><span className={`teacher-status status-${lab.status}`}>{lab.status}</span><div className="teacher-lab-actions">{actions.map(([status, label]) => <button className="outline-button mini" key={status} disabled={busy} onClick={() => onStatus(lab, status)}>{busy ? 'Updating…' : label}</button>)}</div></article>
}

function AnalyticsPage({ dashboard }: { dashboard: DashboardData | null }) {
  const [topicFilter, setTopicFilter] = useState('all')
  const topics = dashboard?.weak_topics ?? []
  const visibleTopics = topics.filter((topic) => topicFilter === 'all' || topic.topic === topicFilter)
  return <>
    <div className="teacher-page-heading"><div><small>LEARNING SIGNALS</small><h2>Analytics</h2><p>Assessment performance is based on recorded diagnosis outcomes; learner mastery is shown only when a profile exists.</p></div></div>
    <div className="teacher-filter-row"><label>Topic<select value={topicFilter} onChange={(event) => setTopicFilter(event.target.value)}><option value="all">All topics</option>{topics.map((topic) => <option key={topic.topic} value={topic.topic}>{topic.topic}</option>)}</select></label><span>Class and time-period filters are unavailable because the API provides workspace-wide, undated analytics.</span></div>
    <section className="teacher-analytics-summary"><article className="teacher-panel"><small>AVERAGE MASTERY</small><strong>{dashboard?.average_mastery != null ? `${Math.round(dashboard.average_mastery * 100)}%` : '—'}</strong><p>Shown when learner profiles are available.</p></article><article className="teacher-panel"><small>ASSESSMENT PERFORMANCE</small><strong>{dashboard?.average_assessment_performance != null ? `${Math.round(dashboard.average_assessment_performance)}%` : '—'}</strong><p>Percentage correct across recorded diagnoses.</p></article><article className="teacher-panel"><small>ACTIVE STUDENTS</small><strong>{dashboard ? dashboard.active_students : '—'}</strong><p>Enrolled students with at least one recorded submission.</p></article></section>
    <section className="teacher-panel"><div className="teacher-panel-heading"><div><small>TOPIC PERFORMANCE</small><h3>Mastery and weak topics</h3></div></div>{visibleTopics.length ? <div className="teacher-topic-bars">{visibleTopics.map((topic) => <div className="teacher-topic-bar" key={topic.topic}><div><strong>{topic.topic}</strong><b>{Math.round(topic.mastery * 100)}%</b></div><span><i style={{ width: `${Math.max(0, Math.min(100, topic.mastery * 100))}%` }} /></span><small>{topic.weak_students.join(', ') || 'No learner names supplied'}</small>{topic.misconception_ids?.length ? <small>Related misconception labels: {topic.misconception_ids.join(', ')}. Frequency counts are unavailable.</small> : null}</div>)}</div> : <EmptyState text="There is insufficient topic data for a reliable trend." />}</section>
    <section className="teacher-panel"><div className="teacher-panel-heading"><div><small>AT-RISK LEARNERS</small><h3>Needs follow-up</h3></div></div>{dashboard?.at_risk_students.length ? <div className="teacher-table-wrap"><table className="teacher-table"><thead><tr><th>Student</th><th>Risk score</th><th>Reported reasons</th></tr></thead><tbody>{dashboard.at_risk_students.map((student) => <tr key={student.student}><td><strong>{student.student}</strong></td><td>{student.risk_score.toFixed(2)}</td><td>{student.reasons.join(', ') || 'No reasons provided'}</td></tr>)}</tbody></table></div> : <EmptyState text="No at-risk learners are reported." />}<p className="teacher-data-note">Risk scores are heuristics derived from stored mastery and active misconception counts; they are not model confidence values.</p></section>
  </>
}

function ProjectsPage({ projects, language, setLanguage }: { projects: Project[]; language: string; setLanguage: (value: string) => void }) {
  return <>
    <div className="teacher-page-heading teacher-heading-action"><div><small>LEARNING PATH EXTENSIONS</small><h2>Projects</h2><p>Recommended practice projects, ranked using the available mastery signals.</p></div><label className="teacher-language-filter">Language<select value={language} onChange={(event) => setLanguage(event.target.value)}><LanguageOptions /></select></label></div>
    {projects.length ? <div className="teacher-project-grid">{projects.map((project) => <article className="teacher-project-card" key={project.title}><div className="teacher-project-top"><span className="teacher-project-icon"><i className="bi bi-terminal" /></span><span className="teacher-status">{project.difficulty}</span></div><h3>{project.title}</h3><p>{project.description}</p><div className="teacher-project-focus"><small>LEARNING OBJECTIVES</small><span>{project.focus.join(' · ') || 'Not provided'}</span></div><div className="teacher-project-fit"><span>Recommendation fit</span><strong>{Math.round(project.fit_score * 100)}%</strong></div></article>)}</div> : <EmptyState text="Project recommendations are unavailable for this language or data set." />}
    <p className="teacher-data-note">The project catalog does not currently expose project detail or learning-path routes.</p>
  </>
}

function EmptyState({ text }: { text: string }) {
  return <div className="teacher-empty-state"><i className="bi bi-inbox" /><p>{text}</p></div>
}

function LanguageOptions() {
  return <><option value="python">Python</option><option value="c">C</option><option value="cpp">C++</option><option value="html">HTML</option></>
}