// Modified 2026 by Sereja Ris for VibecodersCrew (community fork of Kiro Crew).
// See NOTICE and CHANGELOG.md for the nature of the modifications.
import type { ReactNode } from 'react'
import { useRefreshScheduler } from '../hooks/useRefreshScheduler'
import KiroPrerequisiteGate from './KiroPrerequisiteGate'
import CodexSignInGate from './CodexSignInGate'
import { useProvider } from '../providers'

export default function DashboardBootstrap({ children }: { children: ReactNode }) {
  // This must mount outside the prerequisite gate: a stale access cookie may
  // otherwise prevent App from mounting the scheduler that repairs that cookie.
  useRefreshScheduler()
  const provider = useProvider()
  if (provider.state === 'loading') return <>{children}</>
  if (provider.state === 'invalid') return null
  if (provider.id === 'codex') return <CodexSignInGate>{children}</CodexSignInGate>
  return <KiroPrerequisiteGate>{children}</KiroPrerequisiteGate>
}
