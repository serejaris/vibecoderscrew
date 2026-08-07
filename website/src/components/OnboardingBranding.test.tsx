// Modified 2026 by Sereja Ris for VibecodersCrew (community fork of Kiro Crew).
// See NOTICE and CHANGELOG.md for the nature of the modifications.
import { screen, render } from '@testing-library/react'
import { i18next } from '../i18n'
import { ShellAside } from './OnboardingChapterShell'
import { BrandingProvider, useBranding } from '../hooks/useBranding'
import { api } from '../api/client'

vi.mock('../api/client', async importOriginal => {
  const mod = await importOriginal<typeof import('../api/client')>()
  return {
    ...mod,
    api: {
      ...mod.api,
      branding: vi.fn().mockRejectedValue(new Error('branding unavailable')),
    },
  }
})

function BrandingProbe() {
  const { botName } = useBranding()
  return <span>{botName}</span>
}

describe('onboarding branding', () => {
  it('renders the fork brand in the first-run shell', () => {
    render(
      <ShellAside
        copy={{
          ariaLabel: 'Codex setup',
          panelHeadline: 'Connect OpenAI Codex',
          panelBody: 'Use your existing Codex login.',
          panelFootnote: 'Credentials stay managed locally.',
        }}
      />,
    )

    expect(screen.getByText('VibecodersCrew')).toBeInTheDocument()
    expect(document.body.textContent).not.toContain('Kiro Crew')
    expect(document.body.textContent).not.toContain('app.kiro.dev')
  })

  it('uses the fork brand when the runtime branding endpoint is unavailable', () => {
    expect(i18next.language).toBe('en')
    render(
      <BrandingProvider>
        <BrandingProbe />
      </BrandingProvider>,
    )

    expect(screen.getByText('VibecodersCrew')).toBeInTheDocument()
    expect(screen.queryByText('Kiro Crew')).not.toBeInTheDocument()
    expect(screen.queryByText('app.kiro.dev')).not.toBeInTheDocument()
    expect(api.branding).toHaveBeenCalledTimes(1)
  })
})
