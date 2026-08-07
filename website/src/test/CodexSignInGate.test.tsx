// Modified 2026 by Sereja Ris for VibecodersCrew (community fork of Kiro Crew).
// See NOTICE and CHANGELOG.md for the nature of the modifications.
import { act, fireEvent, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { KiroPrerequisiteStatus } from '../api/client'
import CodexSignInGate from '../components/CodexSignInGate'
import { renderWithProviders } from './helpers'

vi.mock('../api/client', () => ({
  api: {
    kiroPrerequisite: vi.fn(),
    loginCodex: vi.fn(),
  },
}))

import { api } from '../api/client'

function status(overrides: Partial<KiroPrerequisiteStatus> = {}): KiroPrerequisiteStatus {
  return {
    provider: 'codex',
    platform: 'Codex App Server',
    installed: true,
    authenticated: false,
    ready: false,
    initial_setup_complete: false,
    can_auto_install: false,
    can_login: true,
    repair_required: false,
    docs_url: 'https://developers.openai.com/codex/cli/',
    setup_allowed: false,
    sandbox_unavailable: false,
    sandbox_failure_kind: '',
    sandbox_detail: '',
    missing_agent_specs: [],
    agent_spec_repair_error: '',
    operation: {
      kind: '',
      status: 'idle',
      message: '',
      detail: '',
      url: '',
      error: '',
    },
    ...overrides,
  }
}

describe('CodexSignInGate', () => {
  beforeEach(() => vi.clearAllMocks())

  it('does not invoke login on mount and starts it only after an explicit click', async () => {
    vi.mocked(api.kiroPrerequisite)
      .mockResolvedValueOnce(status())
      .mockResolvedValue(status({
        operation: {
          kind: 'login',
          status: 'running',
          message: 'Codex sign-in is running.',
          detail: '',
          url: '',
          error: '',
        },
      }))
    vi.mocked(api.loginCodex).mockResolvedValue(status({
      operation: {
        kind: 'login',
        status: 'running',
        message: 'Codex sign-in is running.',
        detail: '',
        url: '',
        error: '',
      },
    }))

    renderWithProviders(<CodexSignInGate><div>Dashboard loaded</div></CodexSignInGate>)

    const login = await screen.findByRole('button', { name: /Sign in to Codex/ })
    expect(api.loginCodex).not.toHaveBeenCalled()
    fireEvent.click(login)
    await waitFor(() => expect(api.loginCodex).toHaveBeenCalledOnce())
    expect(screen.getByText('Codex sign-in is running.')).toBeInTheDocument()
  })

  it('opens the dashboard automatically for an already authenticated Codex provider', async () => {
    vi.mocked(api.kiroPrerequisite).mockResolvedValue(status({
      authenticated: true,
      ready: true,
      initial_setup_complete: true,
    }))

    renderWithProviders(<CodexSignInGate><div>Dashboard loaded</div></CodexSignInGate>)

    expect(await screen.findByText('Dashboard loaded')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Continue/ })).not.toBeInTheDocument()
  })

  it('polls only an explicit login operation and auto-opens after completion', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    try {
      let statusCalls = 0
      const running = status({
        operation: {
          kind: 'login',
          status: 'running',
          message: 'Codex sign-in is running.',
          detail: '',
          url: '',
          error: '',
        },
      })
      const completed = status({
        authenticated: true,
        ready: true,
        initial_setup_complete: true,
        operation: {
          kind: 'login',
          status: 'succeeded',
          message: 'Codex sign-in finished.',
          detail: '',
          url: '',
          error: '',
        },
      })
      vi.mocked(api.kiroPrerequisite).mockImplementation(async () => {
        statusCalls += 1
        if (statusCalls === 1) return status()
        if (statusCalls < 4) return running
        return completed
      })
      vi.mocked(api.loginCodex).mockResolvedValue(running)

      renderWithProviders(<CodexSignInGate><div>Dashboard loaded</div></CodexSignInGate>)
      const login = await screen.findByRole('button', { name: /Sign in to Codex/ })
      expect(statusCalls).toBe(1)

      fireEvent.click(login)
      await waitFor(() => expect(api.loginCodex).toHaveBeenCalledOnce())
      await waitFor(() => expect(screen.getByText('Codex sign-in is running.')).toBeInTheDocument())

      await act(async () => { await vi.advanceTimersByTimeAsync(4_000) })
      expect(await screen.findByText('Dashboard loaded')).toBeInTheDocument()
      const callsAfterCompletion = statusCalls
      await act(async () => { await vi.advanceTimersByTimeAsync(4_000) })
      expect(statusCalls).toBe(callsAfterCompletion)
    } finally {
      vi.useRealTimers()
    }
  })

  it('shows a retry action when the completed login is still not ready', async () => {
    const completed = status({
      operation: {
        kind: 'login',
        status: 'succeeded',
        message: 'Codex sign-in finished.',
        detail: '',
        url: '',
        error: '',
      },
    })
    let statusCalls = 0
    vi.mocked(api.kiroPrerequisite).mockImplementation(async () => {
      statusCalls += 1
      return statusCalls === 1 ? status() : completed
    })
    vi.mocked(api.loginCodex).mockResolvedValue(completed)

    renderWithProviders(<CodexSignInGate><div>Dashboard loaded</div></CodexSignInGate>)
    fireEvent.click(await screen.findByRole('button', { name: /Sign in to Codex/ }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Retry the Codex readiness check.')
    expect(screen.getByRole('button', { name: /Sign in to Codex/ })).toBeEnabled()
  })
})
