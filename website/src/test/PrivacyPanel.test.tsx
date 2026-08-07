// Modified 2026 by Sereja Ris for VibecodersCrew (community fork of Kiro Crew).
// See NOTICE and CHANGELOG.md for the nature of the modifications.
import { describe, expect, it, vi } from 'vitest'
import { screen, within } from '@testing-library/react'
import { renderWithProviders } from './helpers'
import { PrivacyPanel } from '../pages/settings/PrivacyPanel'
import { api } from '../api/client'

vi.mock('../api/client', async importOriginal => {
  const mod = await importOriginal<typeof import('../api/client')>()
  return {
    ...mod,
    api: {
      ...mod.api,
      beaconStatus: vi.fn(),
      patchConfig: vi.fn(),
    },
  }
})

const beaconStatus = vi.mocked(api.beaconStatus)
const patchConfig = vi.mocked(api.patchConfig)

describe('PrivacyPanel', () => {
  it('renders a static disabled status and the local privacy boundary', () => {
    renderWithProviders(<PrivacyPanel />)

    const panel = screen.getByLabelText('Privacy')
    expect(within(panel).getAllByText('Telemetry is off').length).toBeGreaterThan(0)
    expect(within(panel).getByRole('heading', { name: 'Never sent' })).toBeInTheDocument()
    expect(within(panel).getByRole('heading', { name: 'Stays on your device' })).toBeInTheDocument()
    expect(within(panel).queryByRole('switch')).not.toBeInTheDocument()
  })

  it('never queries beacon status or writes telemetry configuration', () => {
    renderWithProviders(<PrivacyPanel />)

    expect(beaconStatus).not.toHaveBeenCalled()
    expect(patchConfig).not.toHaveBeenCalled()
    expect(screen.queryByText(/Send anonymous usage heartbeat/)).not.toBeInTheDocument()
    expect(screen.queryByText(/kirocrew telemetry disable/)).not.toBeInTheDocument()
  })
})
