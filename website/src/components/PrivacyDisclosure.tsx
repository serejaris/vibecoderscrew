// Modified 2026 by Sereja Ris for VibecodersCrew (community fork of Kiro Crew).
// See NOTICE and CHANGELOG.md for the nature of the modifications.
import { EyeOff, HardDrive } from 'lucide-react'
import { i18nT } from '../i18n/t'

/** Legacy command labels kept for compatibility with callers that import them.
 * The rendered privacy surface no longer presents telemetry controls. */
export const COMMANDS = [
  'kirocrew telemetry status',
  'kirocrew telemetry disable',
] as const

// Keys held in an indexed `as const` map of full literals rather than inline on each
// SHELL_COMMANDS entry: check-i18n-keys.mjs resolves a map access to the map's value
// set, but cannot follow a key destructured out of an array of objects, which would
// exempt the call site from key-existence verification.
export const SHELL_LABEL_KEY = {
  macos: 'privacyDisclosure.shellMacOSLinuxLabel',
  powershell: 'privacyDisclosure.shellPowerShellLabel',
  cmd: 'privacyDisclosure.shellWindowsCmdLabel',
} as const

/** The three per-shell env-var forms, keyed by the same shell ids as
 * `SHELL_LABEL_KEY` so a new shell cannot be added without its label. */
export const SHELL_COMMANDS = [
  { shell: 'macos', command: 'export KIROCREW_TELEMETRY_DISABLED=1' },
  { shell: 'powershell', command: "$env:KIROCREW_TELEMETRY_DISABLED = '1'" },
  { shell: 'cmd', command: 'set KIROCREW_TELEMETRY_DISABLED=1' },
] as const satisfies ReadonlyArray<{
  shell: keyof typeof SHELL_LABEL_KEY
  command: string
}>

/** Static status retained for the settings/onboarding route. */
export function TelemetryToggle() {
  return <p className="text-[13px] font-semibold text-text">{i18nT('pages.telemetryPanel.telemetry_is_off')}</p>
}

/** One disclosure section: icon + heading + body. */
function DisclosureSection({
  icon,
  title,
  body,
}: {
  icon: React.ReactNode
  title: string
  body: string
}) {
  return (
    <div>
      <h3 className="text-sm font-semibold tracking-tight text-text-strong mb-1.5 flex items-center gap-2">
        {icon}
        {title}
      </h3>
      <p className="text-sm text-muted leading-relaxed">{body}</p>
    </div>
  )
}

/**
 * The disclosure copy itself — telemetry is disabled, nothing leaves the
 * machine, the never-sent list, and the local-data boundary. Shared verbatim by
 * Settings → Privacy and the onboarding privacy step so the two can never drift;
 * only the surrounding chrome differs.
 */
export function PrivacyDisclosureSections() {
  return (
    <div className="flex flex-col gap-5">
      <div>
        <h3 className="text-sm font-semibold tracking-tight text-text-strong mb-1.5">
          {i18nT('pages.telemetryPanel.telemetry_is_off')}
        </h3>
        <p className="text-sm text-muted leading-relaxed">
          {i18nT('privacyDisclosure.anonymousHeartbeatBody')}
        </p>
      </div>
      <DisclosureSection
        icon={<EyeOff className="lucide-inline" aria-hidden="true" />}
        title={i18nT('privacyDisclosure.dataNeverSentTitle')}
        body={i18nT('privacyDisclosure.dataNeverSentBody')}
      />
      <DisclosureSection
        icon={<HardDrive className="lucide-inline" aria-hidden="true" />}
        title={i18nT('privacyDisclosure.localDataTitle')}
        body={i18nT('privacyDisclosure.localDataBody')}
      />
    </div>
  )
}

/** Compatibility placeholder retained beneath the static status. */
export function PrivacyCommandList() {
  return (
    <p className="text-[13px] text-muted" aria-label={i18nT('privacyDisclosure.controlsTitle')}>
      {i18nT('pages.telemetryPanel.telemetry_is_off')}
    </p>
  )
}
