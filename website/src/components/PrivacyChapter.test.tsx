// Modified 2026 by Sereja Ris for VibecodersCrew (community fork of Kiro Crew).
// See NOTICE and CHANGELOG.md for the nature of the modifications.
import { screen, fireEvent } from '@testing-library/react'
import { renderWithProviders } from '../test/helpers'
import PrivacyChapter from './PrivacyChapter'
import { api } from '../api/client'

vi.mock('../api/client', async importOriginal => {
  const mod = await importOriginal<typeof import('../api/client')>()
  return {
    ...mod,
    api: {
      ...mod.api,
      patchConfig: vi.fn().mockResolvedValue({}),
      themeBoot: vi.fn().mockResolvedValue({ mode: '', color: '', onboarded: false }),
      beaconStatus: vi.fn(),
    },
  }
})

const patchConfig = vi.mocked(api.patchConfig)
const beaconStatus = vi.mocked(api.beaconStatus)

describe('PrivacyChapter', () => {
  beforeEach(() => {
    patchConfig.mockReset()
    patchConfig.mockResolvedValue({})
  })

  it('renders the disclosure and static disabled status', () => {
    renderWithProviders(<PrivacyChapter open onContinue={vi.fn()} />)

    expect(screen.getByRole('heading', { name: 'Privacy' })).toBeInTheDocument()
    expect(screen.getAllByText('Telemetry is off').length).toBeGreaterThan(0)
    expect(screen.getByText('Never sent')).toBeInTheDocument()
    expect(screen.getByText('Stays on your device')).toBeInTheDocument()
    expect(screen.queryByRole('switch')).not.toBeInTheDocument()
  })

  it('shows the chapter name with no step counter', () => {
    renderWithProviders(<PrivacyChapter open onContinue={vi.fn()} />)

    // A single-screen chapter: the eyebrow is the name alone, never "1 of 1".
    const eyebrow = screen.getByText('Privacy', { selector: 'p' })
    expect(eyebrow).toBeInTheDocument()
    expect(eyebrow.textContent).not.toMatch(/\bof\b|·/)
  })

  it('is mandatory: no skip affordance and Escape does not dismiss', () => {
    const onContinue = vi.fn()
    renderWithProviders(<PrivacyChapter open onContinue={onContinue} />)

    expect(screen.queryByRole('button', { name: /skip/i })).not.toBeInTheDocument()
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(onContinue).not.toHaveBeenCalled()
  })

  it('Continue is always enabled and hands off without requiring a choice', () => {
    const onContinue = vi.fn()
    renderWithProviders(<PrivacyChapter open onContinue={onContinue} />)

    const button = screen.getByRole('button', { name: 'Continue' })
    expect(button).toBeEnabled()
    fireEvent.click(button)
    expect(onContinue).toHaveBeenCalledTimes(1)
  })

  it('uses the same left panel copy as the Import setup chapter', () => {
    renderWithProviders(<PrivacyChapter open onContinue={vi.fn()} />)

    // Identical aside copy is what keeps the shared shell's mascots from
    // re-animating across the hand-off.
    expect(screen.getByText('Bring your crew with you.')).toBeInTheDocument()
    expect(
      screen.getByText('Merge-only setup · credentials stay where they are'),
    ).toBeInTheDocument()
  })

  it('does not expose a telemetry write control or query beacon status', () => {
    renderWithProviders(<PrivacyChapter open onContinue={vi.fn()} />)

    expect(screen.queryByRole('switch')).not.toBeInTheDocument()
    expect(patchConfig).not.toHaveBeenCalled()
    expect(beaconStatus).not.toHaveBeenCalled()
  })

  it('renders nothing while closed', () => {
    renderWithProviders(<PrivacyChapter open={false} onContinue={vi.fn()} />)

    expect(screen.queryByRole('heading', { name: 'Privacy' })).not.toBeInTheDocument()
  })
})
