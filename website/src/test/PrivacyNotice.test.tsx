// Modified 2026 by Sereja Ris for VibecodersCrew (community fork of Kiro Crew).
// See NOTICE and CHANGELOG.md for the nature of the modifications.
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import PrivacyNotice, { PRIVACY_NOTICE_STORAGE_KEY } from '../components/PrivacyNotice'

// The first-run banner is a GLANCE-level notice: it states that telemetry and
// install receipts are disabled, then links to Settings → Privacy for the local
// boundary. It deliberately stays short enough to read above the dashboard.
const GLANCE_CLAIMS = [
  'Telemetry',
  'install receipts',
  'disabled',
  'Prompts',
  'files',
  'credentials',
] as const

function renderNotice() {
  return render(
    <MemoryRouter>
      <PrivacyNotice />
      <main id="main-content" tabIndex={-1}>Dashboard content</main>
    </MemoryRouter>,
  )
}

describe('PrivacyNotice', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.restoreAllMocks()
  })

  it('renders once as a labelled, non-modal region with privacy details', () => {
    renderNotice()

    const notice = screen.getByRole('region', { name: 'Telemetry disabled' })
    expect(notice).toHaveAttribute('aria-describedby', 'privacy-notice-description')
    expect(notice).not.toHaveAttribute('aria-modal')
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Privacy details' })).toHaveAttribute(
      'href',
      '/settings?tab=privacy',
    )
    expect(screen.getByRole('link', { name: 'Privacy details' })).not.toHaveFocus()
    expect(screen.getByRole('button', { name: 'Dismiss' })).not.toHaveFocus()
  })

  it('states the cadence and the never-sent categories at a glance', () => {
    renderNotice()

    const description = document.getElementById('privacy-notice-description')
    expect(description).not.toBeNull()
    for (const claim of GLANCE_CLAIMS) {
      expect(description).toHaveTextContent(claim)
    }
    // Stays short enough to actually be read above the dashboard.
    expect(description!.textContent!.length).toBeLessThan(160)
  })

  it('dismisses from the keyboard and persists the first-run marker', async () => {
    const user = userEvent.setup()
    renderNotice()

    await user.tab()
    expect(screen.getByRole('link', { name: 'Privacy details' })).toHaveFocus()
    await user.tab()
    expect(screen.getByRole('button', { name: 'Dismiss' })).toHaveFocus()
    await user.keyboard('{Enter}')

    expect(screen.queryByTestId('privacy-notice')).not.toBeInTheDocument()
    expect(localStorage.getItem(PRIVACY_NOTICE_STORAGE_KEY)).toBe('1')
  })

  it('moves focus to the main landmark after explicit dismissal', async () => {
    const user = userEvent.setup()
    renderNotice()

    await user.click(screen.getByRole('button', { name: 'Dismiss' }))

    await waitFor(() => expect(screen.getByRole('main')).toHaveFocus())
  })

  it('stays hidden after it has been dismissed', () => {
    localStorage.setItem(PRIVACY_NOTICE_STORAGE_KEY, '1')
    renderNotice()
    expect(screen.queryByTestId('privacy-notice')).not.toBeInTheDocument()
  })

  it('shows the disclosure when persisted state cannot be read', () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new DOMException('blocked', 'SecurityError')
    })

    renderNotice()
    expect(screen.getByRole('region', { name: 'Telemetry disabled' })).toBeInTheDocument()
  })

  it('never blocks the current session when persistence is unavailable', async () => {
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new DOMException('blocked', 'SecurityError')
    })
    const user = userEvent.setup()
    renderNotice()

    await user.click(screen.getByRole('button', { name: 'Dismiss' }))
    expect(screen.queryByTestId('privacy-notice')).not.toBeInTheDocument()
  })
})
