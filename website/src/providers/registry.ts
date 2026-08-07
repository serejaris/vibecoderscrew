// Modified 2026 by Sereja Ris for VibecodersCrew (community fork of Kiro Crew).
// See NOTICE and CHANGELOG.md for the nature of the modifications.
import type { ProviderAdapter, ProviderId, ProviderAdapterId, ProviderCapabilities, ProviderLabels } from './types'
import { AcpAdapter } from './adapters/acp'
import { CodexAdapter } from './adapters/codex'

const ADAPTERS: Record<ProviderId, ProviderAdapter> = {
  acp: new AcpAdapter(),
  codex: new CodexAdapter(),
}

const EMPTY_CAPABILITIES: ProviderCapabilities = {
  hooks: false,
  pluginRegistry: false,
  agentTemplates: false,
  usageBilling: false,
  warmPool: false,
  modelResolution: false,
  toolExecution: false,
  subagents: false,
  sandbox: false,
  contextWindow: false,
  modelSwitching: false,
  permissionModes: false,
  sessionResume: false,
  compaction: false,
  reasoningEffort: false,
}

const EMPTY_LABELS: ProviderLabels = {
  sessionProcess: '',
  agentTemplateField: '',
  processCountLabel: '',
  warmPoolDescription: '',
  configFile: '',
  pluginRegistryName: '',
  hooksSection: '',
}

class UnavailableAdapter extends AcpAdapter {
  readonly id: ProviderAdapterId
  readonly state: 'loading' | 'invalid'
  readonly displayName = ''
  readonly capabilities = EMPTY_CAPABILITIES
  readonly labels = EMPTY_LABELS

  constructor(state: 'loading' | 'invalid') {
    super()
    this.state = state
    this.id = state
  }
}

const LOADING_ADAPTER = new UnavailableAdapter('loading')
const INVALID_ADAPTER = new UnavailableAdapter('invalid')

export function getAdapter(id?: string | null): ProviderAdapter {
  if (id == null || id === '') return LOADING_ADAPTER
  return (ADAPTERS as Record<string, ProviderAdapter>)[id] ?? INVALID_ADAPTER
}
