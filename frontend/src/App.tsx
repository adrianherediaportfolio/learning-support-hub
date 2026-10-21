import { type FormEvent, type ReactNode, useCallback, useEffect, useMemo, useState } from 'react'
import {
  Activity,
  ArrowRight,
  BookOpen,
  CalendarDays,
  Check,
  ChevronLeft,
  ChevronRight,
  ClipboardCheck,
  FileText,
  Home,
  LogOut,
  Plus,
  Search,
  ShieldCheck,
  Target,
  Users,
} from 'lucide-react'
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import { api, downloadPdf, setToken } from './api'

type Student = {
  id: number
  first_name: string
  last_name: string
  birth_date: string
  school_year: string
  school: string
  guardian_name: string
  guardian_email: string
  guardian_phone: string
  notes: string
  consent_signed_at: string | null
  archived: boolean
}
type Assessment = { id: number; assessed_at: string; areas: { area: string; score: number; observations: string }[] }
type Goal = { id: number; area: string; description: string; status: string; target_date: string | null }
type Progress = { goal_id: number; rating: number; comment: string }
type GoalProgressPoint = Progress & { date: string }
type SessionRecord = {
  id: number
  scheduled_at: string
  duration_min: number
  status: string
  notes: string
  goal_progress: Progress[]
}
type AgendaRow = { session: SessionRecord; student_first_name: string; student_last_name: string }
type Sentence = { text: string; pictograms: { keyword: string; arasaac_id: number; image_url: string }[] }
type Material = {
  id: number
  title: string
  original_text: string
  adapted_text: string | null
  sentences: Sentence[]
  attribution: string | null
}
type Report = { id: number; start_date: string; end_date: string; body: string }
type Dashboard = {
  today_sessions: AgendaRow[]
  week_sessions: AgendaRow[]
  active_goal_count: number
  pending_consent_count: number
  latest_reports: {
    id: number
    student_id: number
    student_first_name: string
    student_last_name: string
    start_date: string
    end_date: string
    created_at: string
  }[]
}
type TabName = 'Ficha' | 'Evaluación' | 'Objetivos' | 'Sesiones' | 'Materiales' | 'Informes'
type Section = 'Inicio' | 'Alumnado' | 'Agenda' | 'Informes'

const tabs: TabName[] = ['Ficha', 'Evaluación', 'Objetivos', 'Sesiones', 'Materiales', 'Informes']
const navigation: { label: Section; icon: typeof Home }[] = [
  { label: 'Inicio', icon: Home },
  { label: 'Alumnado', icon: Users },
  { label: 'Agenda', icon: CalendarDays },
  { label: 'Informes', icon: FileText },
]
const attribution =
  'Pictogramas: Sergio Palao. Origen: ARASAAC (http://www.arasaac.org). Licencia: CC (BY-NC-SA). Propiedad: Gobierno de Aragón (España)'
const chartColors = ['#4F7D63', '#E07A5F', '#6889A1', '#8C76A7', '#C39138']

function formatDate(value: string, options: Intl.DateTimeFormatOptions = { dateStyle: 'medium' }) {
  return new Intl.DateTimeFormat('es-ES', options).format(new Date(value))
}

function initials(student: Student) {
  return `${student.first_name.slice(0, 1)}${student.last_name.slice(0, 1)}`.toUpperCase()
}

function localDate(value: Date) {
  return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, '0')}-${String(value.getDate()).padStart(2, '0')}`
}

function mondayOf(value: Date) {
  const monday = new Date(value)
  monday.setHours(0, 0, 0, 0)
  monday.setDate(monday.getDate() - ((monday.getDay() + 6) % 7))
  return monday
}

function Login({ onLogin, error }: { onLogin: (email: string, password: string) => void; error: string }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  return (
    <main className="login-shell">
      <section className="login-story">
        <div className="brand-lockup"><span className="brand-mark"><Activity size={23} /></span><span><strong>Apoyo</strong><small>Gabinete pedagógico</small></span></div>
        <div className="login-illustration" aria-hidden="true">
          <svg viewBox="0 0 420 300" role="presentation">
            <path d="M72 242c24-70 67-120 126-120s102 50 126 120" fill="#DDF0E4" />
            <path d="M115 228c17-42 49-70 83-70s66 28 83 70" fill="#FBF7F0" />
            <path d="M124 113c18-46 45-70 82-70s64 24 82 70" fill="none" stroke="#4F7D63" strokeWidth="7" strokeLinecap="round" />
            <path d="M169 180h75v67h-75z" rx="13" fill="#E9E3F5" />
            <path d="M206 180v66M182 200h18M218 200h18" stroke="#4F7D63" strokeWidth="5" strokeLinecap="round" />
            <circle cx="104" cy="91" r="22" fill="#FBEFC9" />
            <circle cx="324" cy="142" r="17" fill="#FBE1D6" />
            <path d="M90 212c-12-18-13-35-3-48 14 11 20 26 15 45M326 221c12-16 15-31 7-45-15 10-22 24-18 43" fill="#E07A5F" />
          </svg>
        </div>
        <p className="eyebrow">Un espacio para acompañar</p>
        <h1>Organiza cada proceso con calma y claridad.</h1>
        <p className="login-copy">Fichas, objetivos y sesiones en un lugar pensado para el trabajo pedagógico de cada día.</p>
        <div className="login-note"><ShieldCheck size={19} /><span>Acceso privado para profesionales del gabinete.</span></div>
      </section>
      <form
        className="login-card"
        onSubmit={(event) => {
          event.preventDefault()
          onLogin(email, password)
        }}
      >
        <p className="eyebrow">Bienvenida</p>
        <h2>Iniciar sesión</h2>
        <p className="muted mb-7">Entra en tu espacio de trabajo.</p>
        <label className="field-label" htmlFor="email">Correo electrónico</label>
        <input id="email" className="field mb-5" type="email" autoComplete="username" value={email} onChange={(event) => setEmail(event.target.value)} required />
        <label className="field-label" htmlFor="password">Contraseña</label>
        <input id="password" className="field mb-6" type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} required />
        {error && <p role="alert" className="error-box mb-4">{error}</p>}
        <button className="button-primary w-full" type="submit">Entrar en mi espacio <ArrowRight size={17} /></button>
        <p className="mt-6 text-center text-xs muted">Tus datos se mantienen dentro de tu espacio privado.</p>
      </form>
    </main>
  )
}

function App() {
  const [signedIn, setSignedIn] = useState(Boolean(localStorage.getItem('learning-support-token')))
  const [section, setSection] = useState<Section>('Inicio')
  const [students, setStudents] = useState<Student[]>([])
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [tab, setTab] = useState<TabName>('Ficha')
  const [search, setSearch] = useState('')
  const [error, setError] = useState('')
  const [adapterEnabled, setAdapterEnabled] = useState(false)
  const [showStudentForm, setShowStudentForm] = useState(false)
  const [refreshKey, setRefreshKey] = useState(0)
  const [assessments, setAssessments] = useState<Assessment[]>([])
  const [goals, setGoals] = useState<Goal[]>([])
  const [sessions, setSessions] = useState<SessionRecord[]>([])
  const [materials, setMaterials] = useState<Material[]>([])
  const [reports, setReports] = useState<Report[]>([])
  const [progress, setProgress] = useState<GoalProgressPoint[]>([])
  const [editingReport, setEditingReport] = useState<Report | null>(null)
  const [agendaSessions, setAgendaSessions] = useState<AgendaRow[]>([])
  const [dashboard, setDashboard] = useState<Dashboard | null>(null)
  const [weekStart, setWeekStart] = useState(() => localDate(mondayOf(new Date())))

  const reloadStudents = useCallback(async () => {
    const data = await api<Student[]>(`/api/students?search=${encodeURIComponent(search)}`)
    setStudents(data)
    if (selectedId && !data.some((student) => student.id === selectedId)) setSelectedId(null)
  }, [search, selectedId])

  useEffect(() => {
    if (!signedIn) return
    void reloadStudents().catch((reason: Error) => setError(reason.message))
    void api<{ adapter_enabled: boolean }>('/api/health')
      .then((data) => setAdapterEnabled(data.adapter_enabled))
      .catch(() => setAdapterEnabled(false))
    void api<Dashboard>('/api/dashboard')
      .then(setDashboard)
      .catch((reason: Error) => setError(reason.message))
  }, [reloadStudents, signedIn, refreshKey])

  useEffect(() => {
    if (!signedIn || !selectedId) return
    const path = `/api/students/${selectedId}`
    const load = async () => {
      try {
        if (tab === 'Evaluación') setAssessments(await api<Assessment[]>(`${path}/assessments`))
        if (tab === 'Objetivos') {
          const [goalData, progressData] = await Promise.all([
            api<Goal[]>(`${path}/goals`),
            api<GoalProgressPoint[]>(`${path}/goal-progress`),
          ])
          setGoals(goalData)
          setProgress(progressData)
        }
        if (tab === 'Sesiones') {
          const [sessionData, goalData] = await Promise.all([
            api<SessionRecord[]>(`${path}/sessions`),
            api<Goal[]>(`${path}/goals`),
          ])
          setSessions(sessionData)
          setGoals(goalData)
        }
        if (tab === 'Materiales') setMaterials(await api<Material[]>(`${path}/materials`))
        if (tab === 'Informes') {
          const data = await api<Report[]>(`${path}/reports`)
          setReports(data)
          setEditingReport(data[0] ?? null)
        }
      } catch (reason) {
        setError(reason instanceof Error ? reason.message : 'No se pudieron cargar los datos.')
      }
    }
    void load()
  }, [refreshKey, selectedId, signedIn, tab])

  useEffect(() => {
    if (!signedIn || section !== 'Agenda') return
    const start = new Date(`${weekStart}T00:00:00`)
    const end = new Date(start)
    end.setDate(end.getDate() + 6)
    void api<AgendaRow[]>(
      `/api/sessions?start=${encodeURIComponent(`${weekStart}T00:00:00`)}&end=${encodeURIComponent(`${localDate(end)}T23:59:59`)}`,
    ).then(setAgendaSessions).catch((reason: Error) => setError(reason.message))
  }, [section, signedIn, weekStart, refreshKey])

  const selected = students.find((student) => student.id === selectedId) ?? null
  const filtered = useMemo(
    () => students.filter((student) => `${student.first_name} ${student.last_name}`.toLowerCase().includes(search.toLowerCase())),
    [search, students],
  )
  const chartData = useMemo(() => {
    const points = new Map<string, Record<string, string | number>>()
    for (const item of progress) {
      const row = points.get(item.date) ?? {
        date: new Date(item.date).toLocaleDateString('es-ES', { day: '2-digit', month: 'short' }),
      }
      row[`goal-${item.goal_id}`] = item.rating
      points.set(item.date, row)
    }
    return [...points.entries()].sort(([left], [right]) => left.localeCompare(right)).map(([, row]) => row)
  }, [progress])

  const login = async (email: string, password: string) => {
    try {
      const result = await api<{ access_token: string }>('/api/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      })
      setToken(result.access_token)
      setSignedIn(true)
      setError('')
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'No se pudo iniciar sesión.')
    }
  }

  const createStudent = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const fields = new FormData(event.currentTarget)
    const values = Object.fromEntries(fields.entries()) as Record<string, string>
    const payload = {
      ...values,
      consent_signed_at: values.consent_signed_at || null,
      archived: fields.has('archived'),
    }
    try {
      const student = await api<Student>('/api/students', { method: 'POST', body: JSON.stringify(payload) })
      setShowStudentForm(false)
      setSelectedId(student.id)
      setTab('Ficha')
      setSection('Alumnado')
      setRefreshKey((value) => value + 1)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'No se pudo guardar la ficha.')
    }
  }

  const createRecord = async (event: FormEvent<HTMLFormElement>, path: string) => {
    event.preventDefault()
    const form = event.currentTarget
    const fields = new FormData(form)
    const values = Object.fromEntries(fields.entries()) as Record<string, string>
    let payload: Record<string, unknown> = values
    if (path.endsWith('/assessments')) {
      payload = {
        assessed_at: values.assessed_at,
        areas: [{ area: values.area, score: Number(values.score), observations: values.observations }],
      }
    }
    if (path.endsWith('/goals')) {
      payload = { ...values, target_date: values.target_date || null, status: 'activo' }
    }
    if (path.endsWith('/sessions')) {
      payload = {
        ...values,
        duration_min: Number(values.duration_min),
        goal_progress: values.goal_id
          ? [{ goal_id: Number(values.goal_id), rating: Number(values.rating), comment: values.comment }]
          : [],
      }
    }
    try {
      await api(path, { method: 'POST', body: JSON.stringify(payload) })
      setRefreshKey((value) => value + 1)
      setError('')
      form.reset()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'No se pudo guardar.')
    }
  }

  const logout = () => {
    setToken(null)
    setSignedIn(false)
    setStudents([])
    setSelectedId(null)
    setDashboard(null)
    setSection('Inicio')
  }

  const goToSection = (destination: Section) => {
    setError('')
    if (destination === 'Informes') {
      const studentId = selectedId ?? students[0]?.id
      if (studentId) {
        setSelectedId(studentId)
        setTab('Informes')
        setSection('Alumnado')
      } else {
        setSection('Informes')
      }
      return
    }
    setSection(destination)
    if (destination === 'Alumnado') setSelectedId(null)
  }

  const adaptMaterial = async (materialId: number) => {
    if (!selectedId) return
    try {
      await api(`/api/students/${selectedId}/materials/${materialId}/adapt`, { method: 'POST' })
      setRefreshKey((value) => value + 1)
      setError('')
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'No se pudo adaptar el material.')
    }
  }

  if (!signedIn) return <Login onLogin={login} error={error} />

  const weekDates = Array.from({ length: 7 }, (_, index) => {
    const value = new Date(`${weekStart}T00:00:00`)
    value.setDate(value.getDate() + index)
    return value
  })
  const moveWeek = (amount: number) => {
    const next = new Date(`${weekStart}T00:00:00`)
    next.setDate(next.getDate() + amount * 7)
    setWeekStart(localDate(next))
  }

  return (
    <div className="app-shell">
      <aside className="desktop-sidebar">
        <div className="brand-lockup"><span className="brand-mark"><Activity size={22} /></span><span><strong>Apoyo</strong><small>Gabinete pedagógico</small></span></div>
        <p className="sidebar-label">Espacio de trabajo</p>
        <nav className="sidebar-nav" aria-label="Secciones principales">
          {navigation.map(({ label, icon: Icon }) => (
            <button key={label} className={`sidebar-link ${section === label || (label === 'Informes' && section === 'Alumnado' && tab === 'Informes') ? 'sidebar-link-active' : ''}`} onClick={() => goToSection(label)}>
              <Icon size={18} />{label}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="professional-card"><span className="avatar avatar-small">GP</span><span><strong>Equipo pedagógico</strong><small>Espacio privado</small></span></div>
          <button className="sidebar-link logout-link" onClick={logout}><LogOut size={18} />Salir</button>
        </div>
      </aside>

      <div className="app-main">
        <header className="mobile-header">
          <div className="brand-lockup"><span className="brand-mark"><Activity size={20} /></span><span><strong>Apoyo</strong><small>Gabinete pedagógico</small></span></div>
          <button className="icon-button" aria-label="Cerrar sesión" onClick={logout}><LogOut size={18} /></button>
        </header>
        <main className="page-content">
          {error && <div role="alert" className="error-box mb-5">{error}</div>}

          {section === 'Inicio' && (
            <div className="space-y-6">
              <section className="welcome-card">
                <div><p className="eyebrow">Tu espacio de hoy</p><h1>Buenos días, equipo.</h1><p>Una vista tranquila para planificar y acompañar cada avance.</p></div>
                <svg viewBox="0 0 220 160" aria-hidden="true"><circle cx="160" cy="45" r="24" fill="#FBEFC9" /><path d="M30 137c18-44 52-70 83-70s65 26 83 70" fill="#DDF0E4" /><path d="M71 134V91h84v43M93 91V67h40v24" fill="none" stroke="#4F7D63" strokeWidth="6" strokeLinecap="round" strokeLinejoin="round" /><path d="M111 107v27M87 107h16M127 107h16" stroke="#E07A5F" strokeWidth="5" strokeLinecap="round" /></svg>
              </section>
              <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4" aria-label="Resumen">
                <div className="summary-card summary-sky"><span><CalendarDays size={19} /></span><strong>{dashboard?.today_sessions.length ?? 0}</strong><small>Sesiones hoy</small></div>
                <div className="summary-card summary-lilac"><span><Target size={19} /></span><strong>{dashboard?.active_goal_count ?? 0}</strong><small>Objetivos activos</small></div>
                <div className="summary-card summary-butter"><span><ClipboardCheck size={19} /></span><strong>{dashboard?.pending_consent_count ?? 0}</strong><small>Consentimientos pendientes</small></div>
                <div className="summary-card summary-mint"><span><Users size={19} /></span><strong>{students.length}</strong><small>Alumnado activo</small></div>
              </section>
              <section className="grid gap-5 xl:grid-cols-[1.2fr_0.8fr]">
                <div className="panel">
                  <div className="section-heading"><div><p className="eyebrow">Planificación cercana</p><h2>Sesiones de hoy</h2></div><button className="text-link" onClick={() => goToSection('Agenda')}>Ver agenda <ArrowRight size={15} /></button></div>
                  <div className="timeline-list">
                    {(dashboard?.today_sessions ?? []).map((row) => (
                      <article key={row.session.id} className="timeline-item">
                        <span className="timeline-dot" /><div><strong>{row.student_first_name} {row.student_last_name}</strong><p>{formatDate(row.session.scheduled_at, { hour: '2-digit', minute: '2-digit' })} · {row.session.duration_min} min</p>{row.session.notes && <small>{row.session.notes}</small>}</div>
                      </article>
                    ))}
                    {!dashboard?.today_sessions.length && <EmptyNote icon={<CalendarDays size={19} />} title="Un día con espacio" text="No hay sesiones programadas para hoy." />}
                  </div>
                  <div className="week-preview"><span>Esta semana</span><strong>{dashboard?.week_sessions.length ?? 0} sesiones programadas</strong></div>
                </div>
                <div className="panel">
                  <div className="section-heading"><div><p className="eyebrow">Seguimiento reciente</p><h2>Últimos informes</h2></div><FileText className="text-forest" size={21} /></div>
                  <div className="stack-list">
                    {(dashboard?.latest_reports ?? []).map((report) => (
                      <button key={report.id} className="recent-report" onClick={() => { setSelectedId(report.student_id); setTab('Informes'); setSection('Alumnado') }}>
                        <span className="report-icon"><FileText size={17} /></span><span className="min-w-0 flex-1"><strong>{report.student_first_name} {report.student_last_name}</strong><small>Periodo {formatDate(report.start_date)} - {formatDate(report.end_date)}</small></span><ChevronRight size={17} />
                      </button>
                    ))}
                    {!dashboard?.latest_reports.length && <EmptyNote icon={<BookOpen size={19} />} title="Aún no hay informes" text="Los borradores recientes aparecerán aquí." />}
                  </div>
                </div>
              </section>
              <div className="footer-note"><ShieldCheck size={16} /> Los datos se muestran solo al equipo profesional autorizado.</div>
            </div>
          )}

          {section === 'Alumnado' && (
            <div className="space-y-5">
              <div className="section-heading page-title"><div><p className="eyebrow">Fichas y acompañamiento</p><h1>Alumnado</h1><p>Consulta cada proceso y sus próximos pasos.</p></div><button className="button-primary" onClick={() => setShowStudentForm((value) => !value)}><Plus size={17} />Nueva ficha</button></div>
              {showStudentForm && <form onSubmit={createStudent} className="panel grid gap-3 sm:grid-cols-2">
                <h2 className="sm:col-span-2">Nueva ficha</h2>
                <input name="first_name" className="field" placeholder="Nombre" required />
                <input name="last_name" className="field" placeholder="Apellidos" required />
                <input name="birth_date" className="field" type="date" required />
                <input name="school_year" className="field" placeholder="Curso escolar" />
                <input name="school" className="field" placeholder="Centro educativo" />
                <input name="guardian_name" className="field" placeholder="Persona tutora" />
                <input name="guardian_email" className="field" type="email" placeholder="Correo de contacto" />
                <input name="guardian_phone" className="field" placeholder="Teléfono de contacto" />
                <input name="consent_signed_at" className="field" type="date" aria-label="Fecha de consentimiento" />
                <textarea name="notes" className="field sm:col-span-2" placeholder="Notas de seguimiento" />
                <button className="button-primary sm:col-span-2" type="submit">Guardar ficha <Check size={16} /></button>
              </form>}
              <section className="panel">
                <label className="search-field"><Search size={17} /><input aria-label="Buscar estudiante" placeholder="Buscar por nombre o apellido" value={search} onChange={(event) => setSearch(event.target.value)} /></label>
                <div className="student-grid">
                  {filtered.map((student) => (
                    <button key={student.id} className={`student-card ${student.id === selectedId ? 'student-card-active' : ''}`} onClick={() => { setSelectedId(student.id); setTab('Ficha'); setError('') }}>
                      <span className="avatar">{initials(student)}</span><span className="min-w-0 flex-1 text-left"><strong>{student.first_name} {student.last_name}</strong><small>{student.school_year || 'Curso por indicar'}</small></span><ChevronRight size={17} />
                    </button>
                  ))}
                  {!filtered.length && <p className="muted p-4">No hay fichas para mostrar.</p>}
                </div>
              </section>
              {selected && (
                <section className="space-y-5">
                  <header className="student-profile panel">
                    <span className="avatar avatar-large">{initials(selected)}</span><div className="min-w-0 flex-1"><p className="eyebrow">Ficha de seguimiento</p><h2>{selected.first_name} {selected.last_name}</h2><div className="profile-meta"><span>{selected.school_year || 'Curso por indicar'}</span><span className={`consent-badge ${selected.consent_signed_at ? 'consent-ok' : 'consent-pending'}`}>{selected.consent_signed_at ? 'Consentimiento registrado' : 'Consentimiento pendiente'}</span></div></div><span className="profile-school">{selected.school || 'Centro sin indicar'}</span>
                  </header>
                  <nav className="tab-list" aria-label="Secciones de la ficha">
                    {tabs.map((name) => <button key={name} className={`tab-button ${tab === name ? 'tab-button-active' : ''}`} onClick={() => { setTab(name); setError('') }}>{name}</button>)}
                  </nav>
                  {tab === 'Ficha' && <div className="panel grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                    <Info label="Fecha de nacimiento" value={formatDate(selected.birth_date)} /><Info label="Centro educativo" value={selected.school || 'Sin indicar'} /><Info label="Persona tutora" value={selected.guardian_name || 'Sin indicar'} /><Info label="Correo de contacto" value={selected.guardian_email || 'Sin indicar'} /><Info label="Teléfono" value={selected.guardian_phone || 'Sin indicar'} /><Info label="Consentimiento" value={selected.consent_signed_at ? formatDate(selected.consent_signed_at) : 'Pendiente'} /><div className="info-card sm:col-span-2 xl:col-span-3"><p>Notas</p><strong>{selected.notes || 'No hay notas registradas.'}</strong></div>
                  </div>}
                  {tab === 'Evaluación' && <div className="space-y-4">
                    <form className="panel grid gap-3 sm:grid-cols-2" onSubmit={(event) => void createRecord(event, `/api/students/${selected.id}/assessments`)}>
                      <h3 className="sm:col-span-2">Nueva evaluación</h3><input name="assessed_at" type="date" className="field" required /><select name="area" className="field"><option value="lectura">Lectura</option><option value="escritura">Escritura</option><option value="calculo">Cálculo</option><option value="atencion">Atención</option><option value="memoria">Memoria</option><option value="lenguaje_oral">Lenguaje oral</option><option value="socioemocional">Socioemocional</option><option value="otra">Otra</option></select><select name="score" className="field"><option value="3">Valoración: 3 de 5</option><option value="1">1 de 5</option><option value="2">2 de 5</option><option value="4">4 de 5</option><option value="5">5 de 5</option></select><input name="observations" className="field" placeholder="Observaciones" /><button className="button-primary sm:col-span-2" type="submit">Guardar evaluación</button>
                    </form>
                    <div className="grid gap-3 md:grid-cols-2">{assessments.map((assessment) => <article key={assessment.id} className="panel"><p className="muted">{formatDate(assessment.assessed_at)}</p><div className="mt-3 flex flex-wrap gap-2">{assessment.areas.map((area, index) => <span key={`${assessment.id}-${index}`} className={`area-chip area-${area.area}`}>{area.area.replace('_', ' ')} · {area.score}/5</span>)}</div>{assessment.areas.map((area, index) => <p key={`${assessment.id}-note-${index}`} className="mt-3 text-sm muted">{area.observations}</p>)}</article>)}{!assessments.length && <EmptyNote icon={<ClipboardCheck size={20} />} title="Sin evaluaciones" text="Añade una primera valoración para empezar." />}</div>
                  </div>}
                  {tab === 'Objetivos' && <div className="space-y-5">
                    <form className="panel grid gap-3 sm:grid-cols-2" onSubmit={(event) => void createRecord(event, `/api/students/${selected.id}/goals`)}>
                      <h3 className="sm:col-span-2">Añadir objetivo</h3><select name="area" className="field"><option value="lectura">Lectura</option><option value="escritura">Escritura</option><option value="calculo">Cálculo</option><option value="atencion">Atención</option><option value="memoria">Memoria</option><option value="lenguaje_oral">Lenguaje oral</option><option value="socioemocional">Socioemocional</option><option value="otra">Otra</option></select><input name="target_date" type="date" className="field" /><input name="description" className="field sm:col-span-2" placeholder="Describe el objetivo" required /><button className="button-primary sm:col-span-2" type="submit">Guardar objetivo</button>
                    </form>
                    {goals.length > 0 && <div className="goal-grid">{goals.map((goal) => {
                      const ratings = progress.filter((item) => item.goal_id === goal.id).map((item) => item.rating)
                      const mean = ratings.length ? ratings.reduce((sum, item) => sum + item, 0) / ratings.length : 0
                      return <article key={goal.id} className="goal-card"><div className="flex items-start justify-between gap-3"><span className={`area-chip area-${goal.area}`}>{goal.area.replace('_', ' ')}</span><span className={`status-pill status-${goal.status}`}>{goal.status}</span></div><h3>{goal.description}</h3><div className="goal-progress"><span style={{ width: `${mean ? mean * 20 : 6}%` }} /></div><p className="muted">{ratings.length ? `Progreso medio ${mean.toFixed(1)} de 5` : 'Aún sin valoraciones'}{goal.target_date ? ` · Meta ${formatDate(goal.target_date)}` : ''}</p></article>
                    })}</div>}
                    <div className="panel chart-panel"><div className="section-heading"><div><p className="eyebrow">Evolución en el tiempo</p><h3>Progreso de objetivos</h3></div><span className="chart-scale">Escala de 1 a 5</span></div>
                      {chartData.length > 0 ? <div role="img" aria-label="Gráfico de progreso de objetivos" className="chart-area"><ResponsiveContainer width="100%" height="100%"><LineChart data={chartData} margin={{ top: 12, right: 15, bottom: 5, left: -18 }}><CartesianGrid stroke="#EDE6DA" strokeDasharray="4 4" /><XAxis dataKey="date" tick={{ fill: '#6B6459', fontSize: 12 }} /><YAxis domain={[1, 5]} ticks={[1, 2, 3, 4, 5]} tick={{ fill: '#6B6459', fontSize: 12 }} /><Tooltip /><Legend />{goals.map((goal, index) => <Line key={goal.id} type="monotone" dataKey={`goal-${goal.id}`} name={goal.description} stroke={chartColors[index % chartColors.length]} strokeWidth={3} connectNulls dot={{ r: 4 }} />)}</LineChart></ResponsiveContainer></div> : <EmptyNote icon={<Target size={20} />} title="El gráfico aparecerá aquí" text="Registra una sesión con valoración para ver la evolución." />}
                    </div>
                  </div>}
                  {tab === 'Sesiones' && <div className="space-y-4">
                    <form className="panel grid gap-3 sm:grid-cols-2" onSubmit={(event) => void createRecord(event, `/api/students/${selected.id}/sessions`)}>
                      <h3 className="sm:col-span-2">Programar sesión</h3><input name="scheduled_at" type="datetime-local" className="field" required /><input name="duration_min" type="number" min="1" max="480" defaultValue="45" className="field" /><select name="status" className="field"><option value="programada">Programada</option><option value="realizada">Realizada</option><option value="cancelada">Cancelada</option></select><input name="notes" className="field" placeholder="Notas de sesión" /><select name="goal_id" className="field"><option value="">Sin seguimiento de objetivo</option>{goals.map((goal) => <option key={goal.id} value={goal.id}>{goal.description}</option>)}</select><select name="rating" className="field"><option value="3">Valoración: 3 de 5</option><option value="1">1 de 5</option><option value="2">2 de 5</option><option value="4">4 de 5</option><option value="5">5 de 5</option></select><input name="comment" className="field sm:col-span-2" placeholder="Comentario de progreso" /><button className="button-primary sm:col-span-2" type="submit">Guardar sesión</button>
                    </form>
                    <div className="panel timeline-list">
                      {sessions.map((session) => <article key={session.id} className="timeline-item"><span className="timeline-dot" /><div><div className="flex flex-wrap items-center gap-2"><strong>{formatDate(session.scheduled_at, { dateStyle: 'medium', timeStyle: 'short' })}</strong><span className="status-pill">{session.status}</span></div><p>{session.duration_min} min · {session.notes || 'Sin notas'}</p>{session.goal_progress.map((item, index) => <small key={`${session.id}-${index}`}>Objetivo {item.goal_id} · {item.rating}/5 · {item.comment}</small>)}</div></article>)}
                      {!sessions.length && <EmptyNote icon={<CalendarDays size={20} />} title="Sin sesiones todavía" text="Las sesiones aparecerán en esta línea de tiempo." />}
                    </div>
                  </div>}
                  {tab === 'Materiales' && <div className="space-y-4">
                    <form className="panel grid gap-3" onSubmit={(event) => void createRecord(event, `/api/students/${selected.id}/materials`)}><h3>Materiales de trabajo</h3><input name="title" className="field" placeholder="Título del material" required /><textarea name="original_text" className="field min-h-28" placeholder="Texto original" required /><button className="button-primary justify-self-start" type="submit">Guardar material</button></form>
                    {materials.map((material) => <article key={material.id} className="panel"><div className="flex flex-wrap items-center justify-between gap-3"><h3>{material.title}</h3>{adapterEnabled && <button className="button-secondary" onClick={() => void adaptMaterial(material.id)}>Adaptar texto</button>}</div><p className="mt-3 whitespace-pre-wrap muted">{material.adapted_text ?? material.original_text}</p>{material.sentences?.map((sentence, index) => <div key={`${material.id}-${index}`} className="sentence-card mt-3"><div className="mb-2 flex flex-wrap gap-2">{sentence.pictograms.map((pictogram) => <img key={pictogram.arasaac_id} src={pictogram.image_url} alt={pictogram.keyword} className="h-16 w-16 object-contain" />)}</div><p>{sentence.text}</p></div>)}{material.adapted_text && <p className="attribution mt-3">{material.attribution || attribution}</p>}</article>)}
                    {!adapterEnabled && <p className="muted">La adaptación de textos no está configurada en este entorno.</p>}
                  </div>}
                  {tab === 'Informes' && <div className="grid gap-5 xl:grid-cols-[260px_1fr]">
                    <aside className="panel h-fit"><button className="button-primary mb-3 w-full" onClick={() => void (async () => {
                      try {
                        const today = new Date().toISOString().slice(0, 10)
                        const report = await api<Report>(`/api/students/${selected.id}/reports`, { method: 'POST', body: JSON.stringify({ start_date: `${today.slice(0, 4)}-01-01`, end_date: today }) })
                        setReports((items) => [report, ...items])
                        setEditingReport(report)
                      } catch (reason) { setError(reason instanceof Error ? reason.message : 'No se pudo crear el informe.') }
                    })()}>Nuevo borrador</button>{reports.map((report) => <button key={report.id} className={`report-item ${report.id === editingReport?.id ? 'report-item-active' : ''}`} onClick={() => setEditingReport(report)}><FileText size={16} />{formatDate(report.start_date)}</button>)}</aside>
                    {editingReport ? <article className="report-paper"><div className="report-toolbar"><div><p className="eyebrow">Documento para revisar</p><h3>Informe para la familia</h3></div><div className="flex gap-2"><button className="button-secondary" onClick={() => void (async () => { try { const updated = await api<Report>(`/api/students/${selected.id}/reports/${editingReport.id}`, { method: 'PUT', body: JSON.stringify({ start_date: editingReport.start_date, end_date: editingReport.end_date, body: editingReport.body }) }); setEditingReport(updated); setReports((items) => items.map((item) => item.id === updated.id ? updated : item)) } catch (reason) { setError(reason instanceof Error ? reason.message : 'No se pudo guardar.') } })()}><Check size={16} />Guardar</button><button className="button-secondary" onClick={() => void downloadPdf(`/api/students/${selected.id}/reports/${editingReport.id}/pdf`)}><FileText size={16} />PDF</button></div></div><p className="report-recipient">Familia de {selected.first_name} {selected.last_name}</p><p className="muted text-sm">Periodo {formatDate(editingReport.start_date)} - {formatDate(editingReport.end_date)}</p><textarea aria-label="Editar informe" className="report-editor" value={editingReport.body} onChange={(event) => setEditingReport({ ...editingReport, body: event.target.value })} /></article> : <div className="panel"><EmptyNote icon={<FileText size={20} />} title="Prepara un informe" text="Crea un borrador para revisar y compartir con la familia." /></div>}
                  </div>}
                </section>
              )}
            </div>
          )}

          {section === 'Agenda' && <div className="space-y-5">
            <div className="section-heading page-title"><div><p className="eyebrow">Planificación semanal</p><h1>Agenda</h1><p>Organiza las sesiones y reserva tiempo para cada proceso.</p></div><div className="week-controls"><button className="icon-button" aria-label="Semana anterior" onClick={() => moveWeek(-1)}><ChevronLeft size={18} /></button><strong>{formatDate(weekDates[0].toISOString())} - {formatDate(weekDates[6].toISOString())}</strong><button className="icon-button" aria-label="Semana siguiente" onClick={() => moveWeek(1)}><ChevronRight size={18} /></button></div></div>
            <section className="agenda-grid">{weekDates.map((day) => {
              const key = localDate(day)
              const dayRows = agendaSessions.filter((row) => row.session.scheduled_at.slice(0, 10) === key)
              return <article className="agenda-day" key={key}><header><strong>{new Intl.DateTimeFormat('es-ES', { weekday: 'short' }).format(day)}</strong><span>{day.getDate()}</span></header>{dayRows.map((row, index) => <div className={`agenda-block agenda-tone-${index % 5}`} key={row.session.id}><strong>{row.session.scheduled_at.slice(11, 16)}</strong><span>{row.student_first_name} {row.student_last_name}</span><small>{row.session.duration_min} min</small></div>)}</article>
            })}</section>
            <section className="mobile-agenda panel"><h2>Sesiones de la semana</h2>{agendaSessions.map((row) => <article className="mobile-agenda-row" key={row.session.id}><span className="agenda-time">{formatDate(row.session.scheduled_at, { weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })}</span><strong>{row.student_first_name} {row.student_last_name}</strong><small>{row.session.duration_min} min · {row.session.status}</small></article>)}{!agendaSessions.length && <EmptyNote icon={<CalendarDays size={20} />} title="Semana despejada" text="No hay sesiones programadas en estas fechas." />}</section>
          </div>}

          {section === 'Informes' && <section className="panel"><div className="section-heading"><div><p className="eyebrow">Documentos recientes</p><h1>Informes</h1><p>Selecciona una ficha para revisar sus borradores.</p></div><FileText className="text-forest" size={23} /></div>{students.length ? <div className="student-grid">{students.map((student) => <button key={student.id} className="student-card" onClick={() => { setSelectedId(student.id); setTab('Informes'); setSection('Alumnado') }}><span className="avatar">{initials(student)}</span><span className="min-w-0 flex-1 text-left"><strong>{student.first_name} {student.last_name}</strong><small>Abrir informes de la ficha</small></span><ChevronRight size={17} /></button>)}</div> : <EmptyNote icon={<FileText size={20} />} title="Sin fichas todavía" text="Añade una ficha para preparar un informe." />}</section>}
        </main>
        <nav className="mobile-nav" aria-label="Navegación móvil">
          {navigation.map(({ label, icon: Icon }) => <button key={label} className={section === label || (label === 'Informes' && section === 'Alumnado' && tab === 'Informes') ? 'mobile-nav-active' : ''} onClick={() => goToSection(label)}><Icon size={19} /><span>{label}</span></button>)}
        </nav>
      </div>
    </div>
  )
}

function Info({ label, value }: { label: string; value: string }) {
  return <div className="info-card"><p>{label}</p><strong>{value}</strong></div>
}

function EmptyNote({ icon, title, text }: { icon: ReactNode; title: string; text: string }) {
  return <div className="empty-note"><span>{icon}</span><strong>{title}</strong><p>{text}</p></div>
}

export default App
