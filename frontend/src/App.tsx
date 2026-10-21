import { type FormEvent, useCallback, useEffect, useMemo, useState } from 'react'
import {
  Activity,
  CalendarDays,
  Check,
  ChevronRight,
  FileText,
  LogOut,
  Plus,
  Search,
  ShieldCheck,
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
type TabName = 'Ficha' | 'Evaluación' | 'Objetivos' | 'Sesiones' | 'Materiales' | 'Informes'
const tabs: TabName[] = ['Ficha', 'Evaluación', 'Objetivos', 'Sesiones', 'Materiales', 'Informes']
const attribution =
  'Pictogramas: Sergio Palao. Origen: ARASAAC (http://www.arasaac.org). Licencia: CC (BY-NC-SA). Propiedad: Gobierno de Aragón (España)'

function Login({ onLogin, error }: { onLogin: (email: string, password: string) => void; error: string }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  return (
    <main className="grid min-h-screen place-items-center px-5">
      <form
        className="panel w-full max-w-md p-8"
        onSubmit={(event) => {
          event.preventDefault()
          onLogin(email, password)
        }}
      >
        <div className="mb-6 flex items-center gap-3">
          <span className="rounded-2xl bg-forest p-3 text-white"><Activity size={22} /></span>
          <div><p className="text-xl font-bold">Apoyo</p><p className="text-sm text-slate-500">Gestión pedagógica</p></div>
        </div>
        <h1 className="mb-2 text-2xl font-bold">Iniciar sesión</h1>
        <p className="mb-6 text-sm text-slate-500">Acceso al espacio profesional del gabinete.</p>
        <label className="field-label" htmlFor="email">Correo electrónico</label>
        <input id="email" className="field mb-4" type="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
        <label className="field-label" htmlFor="password">Contraseña</label>
        <input id="password" className="field mb-5" type="password" value={password} onChange={(event) => setPassword(event.target.value)} required />
        {error && <p role="alert" className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-800">{error}</p>}
        <button className="button-primary w-full" type="submit">Entrar en mi espacio</button>
      </form>
    </main>
  )
}

function App() {
  const [signedIn, setSignedIn] = useState(Boolean(localStorage.getItem('learning-support-token')))
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
  const [agendaSessions, setAgendaSessions] = useState<{ session: SessionRecord; student_first_name: string; student_last_name: string }[]>([])

  const reloadStudents = useCallback(async () => {
    const data = await api<Student[]>(`/api/students?search=${encodeURIComponent(search)}`)
    setStudents(data)
    if (selectedId && !data.some((student) => student.id === selectedId)) setSelectedId(null)
  }, [search, selectedId])

  useEffect(() => {
    if (!signedIn) return
    void reloadStudents().catch((reason: Error) => setError(reason.message))
    void api<{ adapter_enabled: boolean }>('/api/health').then((data) => setAdapterEnabled(data.adapter_enabled)).catch(() => setAdapterEnabled(false))
  }, [reloadStudents, signedIn])

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
    return [...points.entries()]
      .sort(([left], [right]) => left.localeCompare(right))
      .map(([, row]) => row)
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
        areas: [{
          area: values.area,
          score: Number(values.score),
          observations: values.observations,
        }],
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
  }

  const loadAgenda = async () => {
    const start = new Date()
    start.setDate(start.getDate() - start.getDay() + 1)
    const end = new Date(start)
    end.setDate(start.getDate() + 6)
    try {
      const rows = await api<typeof agendaSessions>(
        `/api/sessions?start=${encodeURIComponent(start.toISOString())}&end=${encodeURIComponent(end.toISOString())}`,
      )
      setAgendaSessions(rows)
      setTab('Sesiones')
      setSelectedId(null)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'No se pudo cargar la agenda.')
    }
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

  return (
    <div className="min-h-screen bg-sand text-ink">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-[1500px] items-center justify-between px-5 py-4 lg:px-9">
          <div className="flex items-center gap-3">
            <div className="rounded-xl bg-forest p-2.5 text-white"><Activity size={22} /></div>
            <div><p className="font-bold leading-tight">Apoyo</p><p className="text-xs text-slate-500">Gabinete pedagógico</p></div>
          </div>
          <nav className="flex items-center gap-2">
            <button onClick={() => { setSelectedId(null); void reloadStudents() }} className="nav-link"><Users size={17} /> Alumnado</button>
            <button onClick={() => void loadAgenda()} className="nav-link"><CalendarDays size={17} /> Agenda</button>
            <button onClick={logout} className="nav-link" aria-label="Cerrar sesión"><LogOut size={17} /> Salir</button>
          </nav>
        </div>
      </header>
      <main className="mx-auto grid max-w-[1500px] gap-6 px-5 py-7 lg:grid-cols-[300px_1fr] lg:px-9">
        <aside className="panel h-fit p-5">
          <div className="mb-4 flex items-center justify-between">
            <div><p className="text-xs font-bold uppercase tracking-wider text-forest">Mi espacio</p><h1 className="mt-1 text-xl font-bold">Alumnado</h1></div>
            <button className="icon-button" aria-label="Añadir estudiante" onClick={() => setShowStudentForm((value) => !value)}><Plus size={19} /></button>
          </div>
          <label className="relative mb-4 block">
            <Search className="absolute left-3 top-3 text-slate-400" size={17} />
            <input className="field pl-10" placeholder="Buscar estudiante" value={search} onChange={(event) => setSearch(event.target.value)} />
          </label>
          <div className="space-y-2">
            {filtered.map((student) => (
              <button
                key={student.id}
                onClick={() => { setSelectedId(student.id); setTab('Ficha'); setError('') }}
                className={`student-item ${student.id === selectedId ? 'student-item-active' : ''}`}
              >
                <span className="avatar">{student.first_name.slice(0, 1)}{student.last_name.slice(0, 1)}</span>
                <span className="min-w-0 flex-1 text-left"><span className="block truncate font-semibold">{student.first_name} {student.last_name}</span><span className="block truncate text-xs text-slate-500">{student.school_year || 'Sin curso'}</span></span>
                <ChevronRight size={16} />
              </button>
            ))}
            {filtered.length === 0 && <p className="py-4 text-sm text-slate-500">No hay fichas para mostrar.</p>}
          </div>
          <div className="mt-5 rounded-xl bg-sage p-3 text-xs leading-5 text-forest"><ShieldCheck size={16} className="mb-1" /> Datos protegidos. Cada profesional accede solo a su alumnado.</div>
        </aside>

        <section className="min-w-0">
          {error && <div role="alert" className="mb-4 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-800">{error}</div>}
          {showStudentForm && (
            <form onSubmit={createStudent} className="panel mb-5 grid gap-3 p-5 md:grid-cols-2">
              <h2 className="md:col-span-2 text-lg font-bold">Nueva ficha</h2>
              <input name="first_name" className="field" placeholder="Nombre" required />
              <input name="last_name" className="field" placeholder="Apellidos" required />
                  <input name="birth_date" className="field" type="date" required />
                  <input name="consent_signed_at" className="field" type="datetime-local" aria-label="Fecha de consentimiento" />
              <input name="school_year" className="field" placeholder="Curso escolar" />
              <input name="school" className="field" placeholder="Centro educativo" />
              <input name="guardian_name" className="field" placeholder="Persona tutora" />
              <input name="guardian_email" className="field" type="email" placeholder="Correo de contacto" />
              <input name="guardian_phone" className="field" placeholder="Teléfono" />
              <textarea name="notes" className="field md:col-span-2" placeholder="Notas profesionales" />
              <label className="flex items-center gap-2 text-sm md:col-span-2"><input name="archived" type="checkbox" value="true" /> Archivar ficha</label>
              <button className="button-primary md:col-span-2" type="submit">Guardar ficha</button>
            </form>
          )}

          {!selected && tab === 'Sesiones' ? (
            <div className="panel p-6">
              <div className="mb-5 flex items-center gap-3"><CalendarDays className="text-forest" /><div><h2 className="text-xl font-bold">Agenda semanal</h2><p className="text-sm text-slate-500">Sesiones de todas tus fichas.</p></div></div>
              <button className="button-secondary mb-4" onClick={() => void loadAgenda()}>Actualizar semana</button>
              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                {agendaSessions.map((item) => (
                  <article key={item.session.id} className="rounded-xl border border-slate-200 p-4">
                    <p className="font-bold">{item.student_first_name} {item.student_last_name}</p>
                    <p className="mt-1 text-sm text-slate-600">{new Date(item.session.scheduled_at).toLocaleString('es-ES')}</p>
                    <p className="mt-2 text-xs text-forest">{item.session.duration_min} min · {item.session.status}</p>
                  </article>
                ))}
                {agendaSessions.length === 0 && <p className="text-sm text-slate-500">No hay sesiones esta semana.</p>}
              </div>
            </div>
          ) : selected ? (
            <div className="space-y-5">
              <div className="panel flex flex-col justify-between gap-4 p-6 sm:flex-row sm:items-center">
                <div><p className="text-xs font-bold uppercase tracking-wider text-forest">Ficha del estudiante</p><h2 className="mt-1 text-2xl font-bold">{selected.first_name} {selected.last_name}</h2><p className="mt-1 text-sm text-slate-500">{selected.school_year} · {selected.school || 'Centro sin indicar'}</p></div>
                <div className="flex items-center gap-2 rounded-xl bg-sage px-4 py-3 text-sm text-forest"><ShieldCheck size={18} />{selected.consent_signed_at ? 'Consentimiento registrado' : 'Consentimiento pendiente'}</div>
              </div>
              <div className="flex gap-2 overflow-x-auto border-b border-slate-200">
                {tabs.map((name) => <button key={name} className={`tab-button ${tab === name ? 'tab-button-active' : ''}`} onClick={() => { setTab(name); setError('') }}>{name}</button>)}
              </div>
              {tab === 'Ficha' && (
                <div className="panel grid gap-4 p-6 md:grid-cols-2">
                  <Info label="Fecha de nacimiento" value={new Date(`${selected.birth_date}T00:00:00`).toLocaleDateString('es-ES')} />
                  <Info label="Curso" value={selected.school_year || 'Sin indicar'} />
                  <Info label="Centro educativo" value={selected.school || 'Sin indicar'} />
                  <Info label="Persona tutora" value={selected.guardian_name || 'Sin indicar'} />
                  <Info label="Correo" value={selected.guardian_email || 'Sin indicar'} />
                  <Info label="Teléfono" value={selected.guardian_phone || 'Sin indicar'} />
                  <Info label="Notas" value={selected.notes || 'Sin notas registradas'} />
                  <Info label="Estado" value={selected.archived ? 'Archivada' : 'Activa'} />
                </div>
              )}
              {tab === 'Evaluación' && <div className="space-y-4">
                <form className="panel grid gap-3 p-5 sm:grid-cols-[1fr_1fr_2fr_1fr_auto]" onSubmit={(event) => void createRecord(event, `/api/students/${selected.id}/assessments`)}>
                  <input name="assessed_at" type="date" className="field" required />
                  <select name="area" className="field"><option value="lectura">Lectura</option><option value="escritura">Escritura</option><option value="calculo">Cálculo</option><option value="atencion">Atención</option><option value="memoria">Memoria</option><option value="lenguaje_oral">Lenguaje oral</option><option value="socioemocional">Socioemocional</option><option value="otra">Otra</option></select>
                  <input name="observations" className="field" placeholder="Observaciones del área" />
                  <select name="score" className="field"><option value="3">Nivel 3 de 5</option><option value="1">Nivel 1 de 5</option><option value="2">Nivel 2 de 5</option><option value="4">Nivel 4 de 5</option><option value="5">Nivel 5 de 5</option></select>
                  <button className="button-primary" type="submit">Añadir</button>
                </form>
                <div className="panel divide-y divide-slate-100 p-5">{assessments.map((item) => <article key={item.id} className="py-3"><p className="font-semibold">{new Date(`${item.assessed_at}T00:00:00`).toLocaleDateString('es-ES')}</p>{item.areas.map((area, index) => <p key={`${item.id}-${index}`} className="mt-1 text-sm text-slate-600">{area.area} · {area.score}/5 · {area.observations}</p>)}</article>)}{assessments.length === 0 && <p className="text-sm text-slate-500">Aún no hay evaluaciones.</p>}</div>
              </div>}
              {tab === 'Objetivos' && <div className="grid gap-5 xl:grid-cols-[1fr_1fr]">
                <div className="panel p-5"><h3 className="mb-4 font-bold">Objetivos activos</h3>
                  <form className="mb-5 grid gap-2" onSubmit={(event) => void createRecord(event, `/api/students/${selected.id}/goals`)}>
                    <select name="area" className="field"><option value="lectura">Lectura</option><option value="escritura">Escritura</option><option value="calculo">Cálculo</option><option value="atencion">Atención</option><option value="memoria">Memoria</option><option value="lenguaje_oral">Lenguaje oral</option><option value="socioemocional">Socioemocional</option><option value="otra">Otra</option></select>
                    <input name="description" className="field" placeholder="Descripción del objetivo" required />
                    <input name="target_date" type="date" className="field" />
                    <button className="button-primary" type="submit">Añadir objetivo</button>
                  </form>
                  <div className="space-y-3">{goals.map((goal) => <article key={goal.id} className="rounded-xl bg-sand p-3"><p className="font-semibold">{goal.description}</p><p className="mt-1 text-xs text-forest">{goal.area} · {goal.status}{goal.target_date ? ` · ${goal.target_date}` : ''}</p></article>)}{goals.length === 0 && <p className="text-sm text-slate-500">Registra el primer objetivo.</p>}</div>
                </div>
                <div className="panel p-5"><h3 className="mb-4 font-bold">Progreso a lo largo del tiempo</h3>
                  {progress.length ? <ResponsiveContainer width="100%" height={320}>
                    <LineChart data={chartData} margin={{ top: 8, right: 12, bottom: 4, left: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} />
                      <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                      <YAxis domain={[1, 5]} ticks={[1, 2, 3, 4, 5]} width={28} />
                      <Tooltip />
                      <Legend />
                      {goals.map((goal, index) => (
                        <Line
                          key={goal.id}
                          type="monotone"
                          dataKey={`goal-${goal.id}`}
                          name={goal.description}
                          stroke={['#24564d', '#dc8d56', '#5176a3', '#9a6bab', '#b06e58'][index % 5]}
                          strokeWidth={2}
                          connectNulls
                          activeDot={{ r: 5 }}
                        />
                      ))}
                    </LineChart>
                  </ResponsiveContainer> : <p className="text-sm text-slate-500">El gráfico aparecerá cuando las sesiones incluyan seguimiento.</p>}
                </div>
              </div>}
              {tab === 'Sesiones' && <div className="space-y-4">
                <form className="panel grid gap-3 p-5 sm:grid-cols-2" onSubmit={(event) => void createRecord(event, `/api/students/${selected.id}/sessions`)}>
                  <input name="scheduled_at" type="datetime-local" className="field" required />
                  <input name="duration_min" type="number" min="1" max="480" defaultValue="45" className="field" />
                  <select name="status" className="field"><option value="programada">Programada</option><option value="realizada">Realizada</option><option value="cancelada">Cancelada</option></select>
                  <input name="notes" className="field" placeholder="Notas de sesión" />
                  <select name="goal_id" className="field"><option value="">Sin seguimiento de objetivo</option>{goals.map((goal) => <option key={goal.id} value={goal.id}>{goal.description}</option>)}</select>
                  <select name="rating" className="field"><option value="3">Valoración: 3 de 5</option><option value="1">Valoración: 1 de 5</option><option value="2">Valoración: 2 de 5</option><option value="4">Valoración: 4 de 5</option><option value="5">Valoración: 5 de 5</option></select>
                  <input name="comment" className="field" placeholder="Comentario de progreso" />
                  <button className="button-primary sm:col-span-2" type="submit">Añadir sesión</button>
                </form>
                <div className="panel divide-y divide-slate-100 p-5">{sessions.map((session) => <article key={session.id} className="py-3"><p className="font-semibold">{new Date(session.scheduled_at).toLocaleString('es-ES')} · {session.status}</p><p className="mt-1 text-sm text-slate-600">{session.duration_min} min · {session.notes}</p>{session.goal_progress.map((item, index) => <p key={`${session.id}-${index}`} className="mt-1 text-xs text-forest">Objetivo {item.goal_id} · {item.rating}/5 · {item.comment}</p>)}</article>)}{sessions.length === 0 && <p className="text-sm text-slate-500">Aún no hay sesiones.</p>}</div>
              </div>}
              {tab === 'Materiales' && <div className="space-y-4">
                <form className="panel grid gap-3 p-5" onSubmit={(event) => void createRecord(event, `/api/students/${selected.id}/materials`)}>
                  <input name="title" className="field" placeholder="Título del material" required />
                  <textarea name="original_text" className="field min-h-28" placeholder="Texto original" required />
                  <button className="button-primary justify-self-start" type="submit">Guardar material</button>
                </form>
                {materials.map((material) => <article key={material.id} className="panel p-5">
                  <div className="flex items-center justify-between gap-3"><h3 className="font-bold">{material.title}</h3>{adapterEnabled && <button className="button-secondary" onClick={() => void adaptMaterial(material.id)}>Adaptar texto</button>}</div>
                  <p className="mt-3 whitespace-pre-wrap text-sm text-slate-600">{material.adapted_text ?? material.original_text}</p>
                  {material.sentences?.map((sentence, index) => <div key={`${material.id}-${index}`} className="mt-3 rounded-xl bg-sand p-4"><div className="mb-2 flex flex-wrap gap-2">{sentence.pictograms.map((pictogram) => <img key={pictogram.arasaac_id} src={pictogram.image_url} alt={pictogram.keyword} className="h-16 w-16 object-contain" />)}</div><p>{sentence.text}</p></div>)}
                  {material.adapted_text && <p className="mt-3 rounded-lg bg-sage p-3 text-xs text-forest">{material.attribution || attribution}</p>}
                </article>)}
                {!adapterEnabled && <p className="text-sm text-slate-500">La adaptación de textos no está configurada en este entorno.</p>}
              </div>}
              {tab === 'Informes' && <div className="grid gap-5 xl:grid-cols-[260px_1fr]">
                <aside className="panel h-fit p-4"><button className="button-primary mb-3 w-full" onClick={() => void (async () => {
                  try {
                    const today = new Date().toISOString().slice(0, 10)
                    const report = await api<Report>(`/api/students/${selected.id}/reports`, { method: 'POST', body: JSON.stringify({ start_date: `${today.slice(0, 4)}-01-01`, end_date: today }) })
                    setReports((items) => [report, ...items])
                    setEditingReport(report)
                  } catch (reason) { setError(reason instanceof Error ? reason.message : 'No se pudo crear el informe.') }
                })()}>Nuevo borrador</button>{reports.map((report) => <button key={report.id} className={`report-item ${report.id === editingReport?.id ? 'report-item-active' : ''}`} onClick={() => setEditingReport(report)}><FileText size={16} />{new Date(`${report.start_date}T00:00:00`).toLocaleDateString('es-ES')}</button>)}</aside>
                {editingReport ? <div className="panel p-5"><div className="mb-4 flex flex-wrap items-center justify-between gap-3"><div><h3 className="font-bold">Informe para la familia</h3><p className="text-xs text-slate-500">Puedes revisar y editar el borrador.</p></div><div className="flex gap-2"><button className="button-secondary" onClick={() => void (async () => { try { const updated = await api<Report>(`/api/students/${selected.id}/reports/${editingReport.id}`, { method: 'PUT', body: JSON.stringify({ start_date: editingReport.start_date, end_date: editingReport.end_date, body: editingReport.body }) }); setEditingReport(updated) } catch (reason) { setError(reason instanceof Error ? reason.message : 'No se pudo guardar.') } })()}><Check size={16} /> Guardar</button><button className="button-secondary" onClick={() => void downloadPdf(`/api/students/${selected.id}/reports/${editingReport.id}/pdf`)}>Descargar PDF</button></div></div><textarea className="field min-h-80 leading-7" value={editingReport.body} onChange={(event) => setEditingReport({ ...editingReport, body: event.target.value })} /></div> : <div className="panel p-8 text-center text-sm text-slate-500">Crea un borrador para empezar.</div>}
              </div>}
            </div>
          ) : (
            <div className="panel min-h-96 p-8">
              <p className="text-xs font-bold uppercase tracking-wider text-forest">Organización cercana y clara</p>
              <h2 className="mt-3 max-w-xl text-3xl font-bold">Acompaña cada proceso con una visión completa.</h2>
              <p className="mt-3 max-w-2xl text-slate-600">Gestiona fichas, objetivos, sesiones y materiales desde un espacio privado para tu equipo.</p>
              <div className="mt-8 grid gap-3 sm:grid-cols-3">
                <div className="metric-card"><Users className="text-forest" /><strong>{students.length}</strong><span>fichas activas</span></div>
                <div className="metric-card"><CalendarDays className="text-forest" /><strong>Agenda</strong><span>planificación semanal</span></div>
                <div className="metric-card"><FileText className="text-forest" /><strong>Informes</strong><span>para compartir con familias</span></div>
              </div>
            </div>
          )}
        </section>
      </main>
    </div>
  )
}

function Info({ label, value }: { label: string; value: string }) {
  return <div className="rounded-xl bg-sand p-4"><p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</p><p className="mt-1 break-words font-medium">{value}</p></div>
}

export default App
