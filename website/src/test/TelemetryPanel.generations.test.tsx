// Modified 2026 by Sereja Ris for VibecodersCrew (community fork of Kiro Crew).
// See NOTICE and CHANGELOG.md for the nature of the modifications.
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'

import TelemetryPanel from '../pages/TelemetryPanel'

vi.mock('../api/client', () => ({
  api: { telemetryStartup: vi.fn() },
}))

describe('TelemetryPanel privacy boundary', () => {
  it('renders a static disabled notice without querying or polling analytics', async () => {
    const { api } = await import('../api/client')
    render(<TelemetryPanel />)

    expect(screen.getByText('Telemetry is off')).toBeInTheDocument()
    expect(api.telemetryStartup).not.toHaveBeenCalled()
  })
})
