// Modified 2026 by Sereja Ris for VibecodersCrew (community fork of Kiro Crew).
// See NOTICE and CHANGELOG.md for the nature of the modifications.
import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import DashboardBootstrap from '../components/DashboardBootstrap'

const { refreshScheduler } = vi.hoisted(() => ({
  refreshScheduler: vi.fn(),
}))

vi.mock('../hooks/useRefreshScheduler', () => ({
  useRefreshScheduler: () => refreshScheduler(),
}))

vi.mock('../components/KiroPrerequisiteGate', () => ({
  default: () => <div>Setup gate</div>,
}))

vi.mock('../components/CodexSignInGate', () => ({
  default: () => <div>Codex setup gate</div>,
}))

vi.mock('../providers', () => ({
  useProvider: () => ({ id: 'codex', state: 'ready' }),
}))

describe('DashboardBootstrap', () => {
  it('mounts auth recovery even while the prerequisite gate blocks App', () => {
    render(<DashboardBootstrap><div>App</div></DashboardBootstrap>)

    expect(screen.getByText('Codex setup gate')).toBeInTheDocument()
    expect(screen.queryByText('Setup gate')).not.toBeInTheDocument()
    expect(screen.queryByText('App')).not.toBeInTheDocument()
    expect(refreshScheduler).toHaveBeenCalledOnce()
  })
})
