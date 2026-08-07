// Modified 2026 by Sereja Ris for VibecodersCrew (community fork of Kiro Crew).
// See NOTICE and CHANGELOG.md for the nature of the modifications.
import { createContext, useContext, type ReactNode } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import { getAdapter } from './registry'
import type { ProviderAdapter } from './types'

const defaultAdapter = getAdapter()

const ProviderContext = createContext<ProviderAdapter>(defaultAdapter)

export function ProviderProvider({ children }: { children: ReactNode }) {
  const { data, isError } = useQuery({
    queryKey: ['kirocrewConfig'],
    queryFn: () => api.kirocrewConfig(),
  })
  const provider = (data as { agent?: { provider?: string } } | undefined)?.agent?.provider
  // Keep the context neutral until the persisted config arrives. A Codex
  // default here would mount the Codex sign-in gate for an explicit ACP
  // profile during the first render and could trigger provider-specific reads.
  const adapter = isError ? getAdapter('__invalid__') : getAdapter(data === undefined ? null : provider)

  return <ProviderContext.Provider value={adapter}>{children}</ProviderContext.Provider>
}

export function useProvider(): ProviderAdapter {
  return useContext(ProviderContext)
}
