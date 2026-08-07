// Modified 2026 by Sereja Ris for VibecodersCrew (community fork of Kiro Crew).
// See NOTICE and CHANGELOG.md for the nature of the modifications.
import { useRef, type ReactNode } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  AlertTriangle,
  ArrowRight,
  ExternalLink,
  Loader2,
  LogIn,
  RefreshCw,
} from 'lucide-react'
import { api, type KiroPrerequisiteStatus } from '../api/client'
import {
  PANEL_CLASS,
  SCRIM_CLASS,
  SECTION_CLASS,
  ShellAside,
} from './OnboardingChapterShell'
import { Badge, Btn, Card, SendBtn } from './ui'
import { i18nT } from '../i18n/t'

const QUERY_KEY = ['kiro-prerequisite'] as const
const CODEX_DOCS_URL = 'https://developers.openai.com/codex/cli/'

function SetupShell({ children }: { children: ReactNode }) {
  const label = i18nT('components.codexSignInGate.codex_setup')
  return (
    <main className={SCRIM_CLASS} aria-label={label}>
      <div className={PANEL_CLASS}>
        <ShellAside
          copy={{
            ariaLabel: label,
            panelHeadline: i18nT('components.codexSignInGate.connect_openai_codex'),
            panelBody: i18nT('components.codexSignInGate.use_your_existing_codex_login'),
            panelFootnote: i18nT('components.codexSignInGate.credentials_stay_with_codex_cli'),
          }}
        />
        <section className={SECTION_CLASS}>
          <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">
            <div className="my-auto w-full px-6 py-8 sm:px-10 sm:py-10">{children}</div>
          </div>
        </section>
      </div>
    </main>
  )
}

function OperationProgress({ status }: { status: KiroPrerequisiteStatus }) {
  const operation = status.operation
  if (operation.status === 'idle' && !operation.message) return null
  const running = operation.status === 'running'
  const failed = operation.status === 'failed'
  return (
    <div
      className={`mt-4 rounded-lg border p-3 ${failed ? 'border-danger/20 bg-danger/10' : 'border-border bg-bg-elevated'}`}
      aria-live="polite"
      role={failed ? 'alert' : 'status'}
    >
      <div className={`flex items-start gap-2 text-sm ${failed ? 'text-danger' : 'text-text'}`}>
        {running && <Loader2 className="lucide-inline animate-spin" />}
        {failed && <AlertTriangle className="lucide-inline" />}
        <span>{operation.error || operation.message}</span>
      </div>
      {operation.detail && (
        <pre className="mt-3 max-h-36 overflow-auto whitespace-pre-wrap break-words rounded-md bg-bg p-3 font-mono text-[12px] leading-relaxed text-muted">
          {operation.detail}
        </pre>
      )}
    </div>
  )
}

export default function CodexSignInGate({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()
  const forceProbe = useRef(false)
  const statusQuery = useQuery({
    queryKey: QUERY_KEY,
    queryFn: () => {
      const refresh = forceProbe.current
      forceProbe.current = false
      return api.kiroPrerequisite(refresh)
    },
    // One cached mount check. Login completion or the explicit Check again
    // button performs the only subsequent readiness read. After the explicit
    // login click, poll only the backend's in-memory operation snapshot while
    // it is running; the backend keeps those ticks subprocess-free and runs
    // one local ``codex login status`` check when the operation completes.
    refetchInterval: (query) => (
      query.state.data?.operation.status === 'running' ? 1000 : false
    ),
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  })
  const updateStatus = (status: KiroPrerequisiteStatus) => {
    queryClient.setQueryData(QUERY_KEY, status)
  }
  const loginMutation = useMutation({
    mutationFn: api.loginCodex,
    onSuccess: (status) => {
      updateStatus(status)
      // The POST may finish after Codex has written its credential cache. One
      // explicit invalidation/refetch observes that completion without
      // introducing a readiness poll loop.
      void queryClient.invalidateQueries({ queryKey: QUERY_KEY, refetchType: 'active' })
    },
  })

  // A pending status is unknown. Mount the dashboard without starting login or
  // opening a browser; only the explicit button below can invoke Codex login.
  if (statusQuery.isPending) return <>{children}</>
  const status = statusQuery.data
  if (!status) {
    if (statusQuery.error instanceof Error && 'status' in statusQuery.error && (statusQuery.error as { status?: number }).status === 404) {
      return <>{children}</>
    }
    return (
      <SetupShell>
        <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-danger/10 text-danger">
          <AlertTriangle className="lucide-inline" />
        </div>
        <p className="mt-6 text-[12px] font-bold uppercase tracking-[0.16em] text-danger">
          {i18nT('components.codexSignInGate.setup_check_unavailable')}
        </p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight text-text-strong">
          {i18nT('components.codexSignInGate.could_not_check_codex')}
        </h1>
        <p className="mt-3 max-w-lg text-sm leading-relaxed text-muted">
          {statusQuery.error?.message || i18nT('components.codexSignInGate.retry_codex_check')}
        </p>
        <div className="mt-6">
          <Btn type="button" disabled={statusQuery.isFetching} onClick={() => { forceProbe.current = true; void statusQuery.refetch() }}>
            <RefreshCw className={`lucide-inline ${statusQuery.isFetching ? 'animate-spin' : ''}`} />
            {i18nT('components.kiroPrerequisiteGate.check_again')}
          </Btn>
        </div>
      </SetupShell>
    )
  }

  if (status.ready) return <>{children}</>

  const busy = status.operation.status === 'running' || loginMutation.isPending
  const operationError = loginMutation.error?.message
    || status.operation.error
    || (status.operation.status === 'succeeded'
      ? i18nT('components.codexSignInGate.retry_codex_check')
      : '')
  return (
    <SetupShell>
      <>
        <div className="mb-7">
          <div className="mb-3 flex items-center gap-2 text-[12px] font-semibold tracking-[0.14em] text-accent">
            <span className="uppercase">{i18nT('components.codexSignInGate.codex_setup')}</span>
            <ArrowRight className="lucide-inline" />
            <span>{i18nT('components.codexSignInGate.local_provider')}</span>
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-text-strong">
            {i18nT('components.codexSignInGate.sign_in_to_codex')}
          </h1>
          <p className="mt-2 max-w-xl text-sm leading-relaxed text-muted">
            {i18nT('components.codexSignInGate.codex_sign_in_description')}
          </p>
        </div>

        <Card className="border-accent/60 shadow-[0_10px_35px_var(--accent-glow)]">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 className="flex items-center gap-2 text-base font-semibold text-text-strong">
                <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent-subtle text-accent">
                  <LogIn className="lucide-inline" />
                </span>
                {i18nT('components.codexSignInGate.openai_codex')}
              </h2>
              <p className="mt-2 text-sm leading-relaxed text-muted">
                {status.installed
                  ? i18nT('components.codexSignInGate.codex_cli_detected')
                  : i18nT('components.codexSignInGate.codex_cli_not_detected')}
              </p>
            </div>
            <Badge variant="aim">
              {i18nT('components.kiroPrerequisiteGate.required')}
            </Badge>
          </div>

          <div className="mt-4 flex flex-wrap items-center gap-3">
            <SendBtn type="button" disabled={busy} onClick={() => loginMutation.mutate()}>
              {busy
                ? <><Loader2 className="lucide-inline animate-spin" /> {i18nT('components.codexSignInGate.signing_in')}</>
                : <><LogIn className="lucide-inline" /> {i18nT('components.codexSignInGate.sign_in_to_codex')}</>}
            </SendBtn>
            <a
              className="inline-flex items-center gap-1.5 text-[13px] font-medium text-accent hover:underline focus-ring"
              href={CODEX_DOCS_URL}
              target="_blank"
              rel="noopener noreferrer"
            >
              {i18nT('components.codexSignInGate.installation_guide')} <ExternalLink className="lucide-inline" />
            </a>
          </div>
          {!status.ready && <OperationProgress status={status} />}
        </Card>

        {operationError && (
          <div className="mb-4 flex items-start gap-2 rounded-lg border border-danger/20 bg-danger/10 p-3 text-sm text-danger" role="alert">
            <AlertTriangle className="lucide-inline" />
            <span>{operationError}</span>
          </div>
        )}

        <div className="flex items-center justify-between gap-4 border-t border-border pt-5">
          <p className="text-[13px] text-muted" aria-live="polite">
            {i18nT('components.codexSignInGate.codex_sign_in_footer')}
          </p>
          <Btn type="button" disabled={busy || statusQuery.isFetching} onClick={() => { forceProbe.current = true; void statusQuery.refetch() }}>
            <RefreshCw className={`lucide-inline ${statusQuery.isFetching ? 'animate-spin' : ''}`} />
            {i18nT('components.kiroPrerequisiteGate.check_again')}
          </Btn>
        </div>
      </>
    </SetupShell>
  )
}
