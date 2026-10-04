import { FormEvent, useEffect, useState } from 'react'
import {
  addInstitutionMember,
  createInstitution,
  enrollInstitutionStudent,
  getInstitutionClasses,
  getInstitutionMembers,
  getInstitutionReport,
  getInstitutions,
  InstitutionClass,
  InstitutionMember,
  InstitutionReport,
  InstitutionSummary,
  linkInstitutionClass,
  listClasses,
  removeInstitutionMember,
  unlinkInstitutionClass,
} from './services/api'
import { AuthenticatedUser } from './services/auth'

export default function InstitutionDashboard({ user, onLogout, onBack }: {
  user: AuthenticatedUser
  onLogout: () => Promise<void>
  onBack: () => void
}) {
  const [institutions, setInstitutions] = useState<InstitutionSummary[]>([])
  const [institutionId, setInstitutionId] = useState<number | null>(null)
  const [members, setMembers] = useState<InstitutionMember[]>([])
  const [classes, setClasses] = useState<InstitutionClass[]>([])
  const [availableClasses, setAvailableClasses] = useState<Array<{ id: number; name: string; language: string }>>([])
  const [report, setReport] = useState<InstitutionReport | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [refreshKey, setRefreshKey] = useState(0)
  const [newName, setNewName] = useState('')
  const [memberEmail, setMemberEmail] = useState('')
  const [memberRole, setMemberRole] = useState<'admin' | 'teacher' | 'student'>('teacher')
  const [selectedClassId, setSelectedClassId] = useState('')
  const [selectedStudentId, setSelectedStudentId] = useState('')
  const [enrollmentClassId, setEnrollmentClassId] = useState('')

  useEffect(() => {
    let active = true
    setLoading(true)
    getInstitutions().then(records => {
      if (!active) return
      setInstitutions(records)
      setInstitutionId(current => current && records.some(item => item.id === current) ? current : records[0]?.id ?? null)
      setError('')
    }).catch(cause => {
      if (active) setError(cause instanceof Error ? cause.message : 'Institutions could not be loaded.')
    }).finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [refreshKey, user.id])

  useEffect(() => {
    if (institutionId === null) {
      setMembers([])
      setClasses([])
      setAvailableClasses([])
      setReport(null)
      return
    }
    let active = true
    const institution = institutions.find(item => item.id === institutionId)
    const memberRequest = institution?.role === 'admin' || institution?.role === 'teacher'
      ? getInstitutionMembers(institutionId)
      : Promise.resolve([] as InstitutionMember[])
    const reportRequest = institution?.role === 'admin'
      ? getInstitutionReport(institutionId)
      : Promise.resolve(null)
    const classRequest = getInstitutionClasses(institutionId)
    const availableRequest = institution?.role === 'admin' || institution?.role === 'teacher'
      ? listClasses(user.id)
      : Promise.resolve([])
    Promise.all([memberRequest, reportRequest, classRequest, availableRequest]).then(([nextMembers, nextReport, nextClasses, nextAvailable]) => {
      if (!active) return
      setMembers(nextMembers)
      setReport(nextReport)
      setClasses(nextClasses)
      setAvailableClasses(nextAvailable.filter(item => !nextClasses.some(linked => linked.id === item.id)))
      setError('')
    }).catch(cause => {
      if (active) setError(cause instanceof Error ? cause.message : 'Institution details could not be loaded.')
    })
    return () => { active = false }
  }, [institutionId, institutions, refreshKey, user.id])

  const institution = institutions.find(item => item.id === institutionId)
  const canManage = institution?.role === 'admin'
  const canTeach = canManage || institution?.role === 'teacher'
  const studentMembers = members.filter(member => member.role === 'student' && member.status === 'active')

  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      const created = await createInstitution(newName.trim())
      setNewName('')
      setInstitutionId(created.id)
      setNotice('Institution created.')
      setRefreshKey(key => key + 1)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Institution could not be created.')
    } finally { setBusy(false) }
  }

  async function addMember(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (institutionId === null) return
    setBusy(true)
    setError('')
    try {
      await addInstitutionMember(institutionId, { email: memberEmail.trim(), role: memberRole })
      setMemberEmail('')
      setNotice('Institution member added.')
      setRefreshKey(key => key + 1)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Member could not be added.')
    } finally { setBusy(false) }
  }

  async function removeMember(userId: number) {
    if (institutionId === null) return
    setBusy(true)
    setError('')
    try {
      await removeInstitutionMember(institutionId, userId)
      setNotice('Institution member removed.')
      setRefreshKey(key => key + 1)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Member could not be removed.')
    } finally { setBusy(false) }
  }

  async function linkClass(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (institutionId === null || !selectedClassId) return
    setBusy(true)
    setError('')
    try {
      await linkInstitutionClass(institutionId, Number(selectedClassId))
      setSelectedClassId('')
      setNotice('Class linked to institution.')
      setRefreshKey(key => key + 1)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Class could not be linked.')
    } finally { setBusy(false) }
  }

  async function enrollStudent(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (institutionId === null || !selectedStudentId || !enrollmentClassId) return
    setBusy(true)
    setError('')
    try {
      await enrollInstitutionStudent(institutionId, Number(enrollmentClassId), Number(selectedStudentId))
      setNotice('Student enrolled in class.')
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Student could not be enrolled.')
    } finally { setBusy(false) }
  }

  async function unlinkClass(classId: number) {
    if (institutionId === null) return
    setBusy(true)
    setError('')
    try {
      await unlinkInstitutionClass(institutionId, classId)
      setNotice('Class unlinked from institution.')
      setRefreshKey(key => key + 1)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Class could not be unlinked.')
    } finally { setBusy(false) }
  }

  return <div className="institution-app">
    <header className="institution-topbar"><strong>Re:Learn <span>/ Institution</span></strong><div><button className="outline-button mini" onClick={onBack}>Back to workspace</button><button className="text-button" onClick={() => void onLogout()}>Log out</button></div></header>
    <main className="institution-page">
      <div className="institution-heading"><div><small>INSTITUTION WORKSPACE</small><h1>Institutions</h1><p>Membership, classes, and reports from connected records.</p></div>{institutions.length > 0 && <label>Institution<select value={institutionId ?? ''} onChange={event => setInstitutionId(Number(event.target.value))}>{institutions.map(item => <option key={item.id} value={item.id}>{item.name} · {item.role}</option>)}</select></label>}</div>
      {notice && <p className="institution-notice" role="status">{notice}</p>}
      {error && <p className="error" role="alert">{error}</p>}
      {loading ? <p>Loading institutions…</p> : !institutions.length ? <section className="institution-panel"><h2>No institution memberships</h2><p>This account is not currently a member of an institution.</p>{user.role === 'admin' && <form className="institution-form" onSubmit={create}><label>Institution name<input required minLength={2} maxLength={180} value={newName} onChange={event => setNewName(event.target.value)} /></label><button className="primary mini" disabled={busy}>{busy ? 'Creating…' : 'Create institution'}</button></form>}</section> : institution && <>
        {canManage && report && <section className="institution-metrics">{[
          ['Members', report.member_count], ['Teachers', report.teacher_count], ['Students', report.student_count],
          ['Classes', report.class_count], ['Published assignments', report.published_assignment_count], ['Attempts', report.attempt_count],
        ].map(([label, value]) => <article className="institution-metric" key={label}><small>{label}</small><strong>{value}</strong></article>)}<article className="institution-metric"><small>Average score</small><strong>{report.average_score === null ? '—' : `${Math.round(report.average_score)}%`}</strong></article></section>}
        <section className="institution-panel"><div className="institution-section-heading"><div><small>CONNECTED CLASSES</small><h2>Classes</h2></div><span>{classes.length} linked</span></div>
          {classes.length ? <div className="institution-class-list">{classes.map(classItem => <article key={classItem.id}><div><strong>{classItem.name}</strong><small>{classItem.language} · Teacher #{classItem.teacher_id}</small></div><span className="teacher-status">Linked</span>{(canManage || classItem.teacher_id === user.id) && <button className="outline-button mini" disabled={busy} onClick={() => void unlinkClass(classItem.id)}>Unlink</button>}</article>)}</div> : <p>No classes are linked to this institution.</p>}
          {canTeach && availableClasses.length > 0 && <form className="institution-inline-form" onSubmit={linkClass}><label>Link one of your classes<select required value={selectedClassId} onChange={event => setSelectedClassId(event.target.value)}><option value="">Choose a class</option>{availableClasses.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label><button className="primary mini" disabled={busy || !selectedClassId}>Link class</button></form>}
          {canTeach && studentMembers.length > 0 && classes.length > 0 && <form className="institution-inline-form" onSubmit={enrollStudent}><label>Student<select required value={selectedStudentId} onChange={event => setSelectedStudentId(event.target.value)}><option value="">Choose a student</option>{studentMembers.map(item => <option key={item.user_id} value={item.user_id}>{item.name} · {item.email}</option>)}</select></label><label>Class<select required value={enrollmentClassId} onChange={event => setEnrollmentClassId(event.target.value)}><option value="">Choose a class</option>{classes.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label><button className="primary mini" disabled={busy || !selectedStudentId || !enrollmentClassId}>Enroll student</button></form>}
        </section>
        {(canManage || institution.role === 'teacher') && <section className="institution-panel"><div className="institution-section-heading"><div><small>MEMBERSHIP</small><h2>Members</h2></div><span>{members.length} active</span></div>
          {canManage && <><p className="institution-data-note">Members must sign in once before they can be added.</p><form className="institution-inline-form" onSubmit={addMember}><label>Email<input required type="email" value={memberEmail} onChange={event => setMemberEmail(event.target.value)} placeholder="member@example.edu" /></label><label>Role<select value={memberRole} onChange={event => setMemberRole(event.target.value as typeof memberRole)}><option value="teacher">Teacher</option><option value="student">Student</option><option value="admin">Admin</option></select></label><button className="primary mini" disabled={busy}>Add member</button></form></>}
          {members.length ? <div className="institution-member-list">{members.map(member => <article key={member.user_id}><div><strong>{member.name}</strong><small>{member.email || 'No verified email'} · {member.role}</small></div>{canManage && member.role !== 'admin' && <button className="outline-button mini" disabled={busy} onClick={() => void removeMember(member.user_id)}>Remove</button>}</article>)}</div> : <p>No institution members are available to this role.</p>}
        </section>}
        {canManage && !report && <p className="institution-data-note">Institution reports are unavailable until the backend returns a report for this institution.</p>}
      </>}
    </main>
  </div>
}