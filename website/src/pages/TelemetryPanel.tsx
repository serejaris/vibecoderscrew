// Modified 2026 by Sereja Ris for VibecodersCrew (community fork of Kiro Crew).
// See NOTICE and CHANGELOG.md for the nature of the modifications.
import { i18nT } from '../i18n/t'

/**
 * Compatibility route for the former developer telemetry panel.
 *
 * The source-only build does not collect or poll startup analytics.  Keeping a
 * small static route avoids breaking bookmarks and downstream navigation while
 * making the privacy boundary explicit.
 */
export default function TelemetryPanel() {
  return (
    <div className="flex-1 min-h-0 p-6">
      <div className="border border-border bg-card rounded-xl p-4 text-sm text-muted">
        {i18nT('pages.telemetryPanel.telemetry_is_off')}
      </div>
    </div>
  )
}
