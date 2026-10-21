import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import App from './App'

const students = [
  { id: 1, first_name: 'Lucía', last_name: 'Prueba', birth_date: '2015-05-12', school_year: '4º Primaria', school: 'Centro Arcoíris', guardian_name: '', guardian_email: '', guardian_phone: '', notes: '', consent_signed_at: null, archived: false },
  { id: 2, first_name: 'Mateo', last_name: 'Demo', birth_date: '2014-03-04', school_year: '5º Primaria', school: 'Colegio del Sol', guardian_name: '', guardian_email: '', guardian_phone: '', notes: '', consent_signed_at: '2025-01-01', archived: false },
]
const report = { id: 8, start_date: '2025-01-01', end_date: '2025-02-01', body: 'Borrador inicial' }

function response(data: unknown, status = 200) {
  return { ok: status >= 200 && status < 300, status, json: async () => data }
}

function mockApi(overrides: (url: string, init?: RequestInit) => unknown = () => undefined) {
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input)
    const custom = overrides(url, init)
    if (custom !== undefined) return response(custom)
    if (url.includes('/api/auth/login')) return response({ access_token: 'test-token' })
    if (url.includes('/api/health')) return response({ adapter_enabled: false })
    if (url.includes('/api/dashboard')) return response({ today_sessions: [], week_sessions: [], active_goal_count: 1, pending_consent_count: 1, latest_reports: [] })
    if (url.includes('/goal-progress')) return response([{ goal_id: 3, date: '2025-01-20', rating: 4, comment: 'Buen avance' }])
    if (url.includes('/goals')) return response([{ id: 3, area: 'lectura', description: 'Leer frases breves', status: 'activo', target_date: null }])
    if (url.includes('/reports')) return response([report])
    if (url.includes('/materials')) return response([])
    if (url.includes('/api/students')) return response(students)
    return response({})
  }))
}

describe('Apoyo', () => {
  beforeEach(() => localStorage.clear())
  afterEach(() => vi.unstubAllGlobals())

  it('shows the Spanish login form', () => {
    render(<App />)
    expect(screen.getByRole('heading', { name: 'Iniciar sesión' })).toBeInTheDocument()
    expect(screen.getByLabelText('Correo electrónico')).toBeInTheDocument()
  })

  it('filters the student list by name', async () => {
    localStorage.setItem('learning-support-token', 'test-token')
    mockApi()
    render(<App />)
    fireEvent.click(screen.getAllByRole('button', { name: 'Alumnado' })[0])
    await screen.findByText('Mateo Demo')
    fireEvent.change(screen.getByLabelText('Buscar estudiante'), { target: { value: 'lucía' } })
    await waitFor(() => expect(screen.queryByText('Mateo Demo')).not.toBeInTheDocument())
    expect(screen.getByText('Lucía Prueba')).toBeInTheDocument()
  })

  it('renders the goals chart with progress data', async () => {
    localStorage.setItem('learning-support-token', 'test-token')
    mockApi()
    render(<App />)
    fireEvent.click(screen.getAllByRole('button', { name: 'Alumnado' })[0])
    await screen.findByText('Lucía Prueba')
    fireEvent.click(screen.getByText('Lucía Prueba'))
    fireEvent.click(screen.getByRole('button', { name: 'Objetivos' }))
    expect(await screen.findByRole('img', { name: 'Gráfico de progreso de objetivos' })).toBeInTheDocument()
  })

  it('saves an edited report', async () => {
    localStorage.setItem('learning-support-token', 'test-token')
    mockApi((url, init) => url.includes('/reports/8') && init?.method === 'PUT' ? report : undefined)
    render(<App />)
    fireEvent.click(screen.getAllByRole('button', { name: 'Alumnado' })[0])
    await screen.findByText('Lucía Prueba')
    fireEvent.click(screen.getAllByRole('button', { name: 'Informes' })[0])
    const editor = await screen.findByLabelText('Editar informe')
    fireEvent.change(editor, { target: { value: 'Informe revisado' } })
    fireEvent.click(screen.getByRole('button', { name: /Guardar/ }))
    await waitFor(() => expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/reports/8'),
      expect.objectContaining({ method: 'PUT', body: expect.stringContaining('Informe revisado') }),
    ))
  })

  it('hides material adaptation when the adapter is disabled', async () => {
    localStorage.setItem('learning-support-token', 'test-token')
    mockApi()
    render(<App />)
    fireEvent.click(screen.getAllByRole('button', { name: 'Alumnado' })[0])
    await screen.findByText('Lucía Prueba')
    fireEvent.click(screen.getByText('Lucía Prueba'))
    fireEvent.click(screen.getByRole('button', { name: 'Materiales' }))
    await screen.findByText('La adaptación de textos no está configurada en este entorno.')
    expect(screen.queryByRole('button', { name: 'Adaptar texto' })).not.toBeInTheDocument()
  })

  it('shows API failures on the login form', async () => {
    mockApi((url) => url.includes('/api/auth/login') ? undefined : undefined)
    vi.stubGlobal('fetch', vi.fn(async () => response({ detail: 'No se pudo iniciar sesión.' }, 401)))
    render(<App />)
    fireEvent.change(screen.getByLabelText('Correo electrónico'), { target: { value: 'demo@example.com' } })
    fireEvent.change(screen.getByLabelText('Contraseña'), { target: { value: 'incorrecta' } })
    fireEvent.click(screen.getByRole('button', { name: 'Entrar en mi espacio' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('No se pudo iniciar sesión.')
  })
})
