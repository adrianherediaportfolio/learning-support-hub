import { fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import App from './App'

describe('Learning Support Hub', () => {
  beforeEach(() => {
    localStorage.clear()
  })
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('shows a Spanish login form', () => {
    render(<App />)
    expect(screen.getByRole('heading', { name: 'Iniciar sesión' })).toBeInTheDocument()
    expect(screen.getByLabelText('Correo electrónico')).toBeInTheDocument()
  })

  it('opens the student workspace after login', async () => {
    vi.stubGlobal('fetch', vi.fn().mockImplementation(async (url: string) => ({
      ok: true,
      status: 200,
      json: async () => (
        url.includes('/api/auth/login')
          ? { access_token: 'test-token' }
          : url.includes('/api/health')
            ? { adapter_enabled: false }
            : []
      ),
    })))
    render(<App />)
    fireEvent.change(screen.getByLabelText('Correo electrónico'), { target: { value: 'demo@example.com' } })
    fireEvent.change(screen.getByLabelText('Contraseña'), { target: { value: 'Demo-1234' } })
    fireEvent.click(screen.getByRole('button', { name: 'Entrar en mi espacio' }))
    expect(await screen.findByRole('heading', { name: 'Alumnado' })).toBeInTheDocument()
  })
})
