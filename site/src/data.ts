// Modified 2026 by Sereja Ris for VibecodersCrew (community fork of Kiro Crew). See NOTICE and MODIFICATIONS.md.

export const FEATURES = [
  { icon: '01', title: 'Multi-Session Chat', desc: 'Tabbed sessions with streaming markdown, inline tool calls, TTS, and Virtuoso-powered rendering. CLI, Slack, Dashboard, or TUI.', tag: 'Core' },
  { icon: '02', title: 'Agent Orchestration', desc: 'Hot-swap multiple agent types per thread. Discovery, warm session pool, conductor skill routing.', tag: 'AI' },
  { icon: '03', title: 'Cron & Heartbeat', desc: 'Recurring jobs, one-shot timers, skip-dates, and a self-healing heartbeat loop that survives gateway restarts.', tag: 'Ops' },
  { icon: '04', title: 'Persistent Memory', desc: 'Episodic + semantic + vector memory. Learns corrections, tracks projects, decays history over 90 days.', tag: 'AI' },
  { icon: '05', title: 'Parallel Subagents', desc: 'Fan-out independent tasks to parallel agents. Results auto-inject as completion events.', tag: 'Core' },
  { icon: '06', title: 'Autonomous Task Runner', desc: 'Give it a spec, walk away. Git-isolated execution, checkpoint resume, retry + replan, learn from failures.', tag: 'AI' },
  { icon: '07', title: '100+ MCP Tools', desc: 'GitHub, CI/CD, issue trackers, calendars, email — all via configured Model Context Protocol servers.', tag: 'Ops' },
  { icon: '08', title: 'Channels & Dashboard', desc: 'Same agent, same context. Optional channel integrations, vision, and configurable speech tools.', tag: 'Core' },
  { icon: '09', title: 'Trust & Security', desc: 'Four-tier approval. 91+ tamper-resistant deny patterns. HMAC audit trail. Sandbox mode.', tag: 'Ops' },
];

export const TAG_CLS: Record<string, string> = {
  Core: 'bg-indigo-500/10 text-indigo-400',
  AI: 'bg-amber-300/10 text-amber-300',
  Ops: 'bg-green-500/10 text-green-400',
  UX: 'bg-rose-500/10 text-rose-400',
};

export const ARCH = [
  { label: 'Channels / Dashboard', sub: 'Local gateway + optional integrations' },
  { label: 'Gateway', sub: 'Python async orchestrator' },
  { label: 'Session Pool', sub: 'Warm agent processes' },
  { label: 'Model Provider', sub: 'Configured by you' },
  { label: 'MCP Servers', sub: '12+ tool servers' },
];

export const TERMINAL_LINES = [
  { prompt: true, text: 'vibecoderscrew gateway' },
  { text: 'VibecodersCrew source build starting...' },
  { text: '   Dashboard:  ', hl: 'http://localhost:5476' },
  { text: '   Channels:   ', hl: 'configured locally' },
  { text: '   MCP:        ', hl: 'configured servers loaded' },
  { text: '   Agents:     ', hl: 'ready' },
  { text: '   Memory:     ', hl: 'vector + episodic + semantic' },
  { text: '   Cron:       ', hl: '3 jobs scheduled' },
  { comment: '   Ready. Open the dashboard or connect a configured channel.' },
];

export const IN_ACTION = [
  { label: 'Voice', user: '[sends a voice memo in Slack]', bot: 'Transcribed: "Can you check if the deployment to prod finished?"\nChecking your pipeline now — Deployment d-4829 completed 12 minutes ago. All health checks passing.' },
  { label: 'Oncall', user: "who's on call for MyService?", bot: '@janedoe (secondary, started Monday). Primary is @johndoe. Want me to page them?' },
  { label: 'Cron', user: 'every weekday at 9am give me a pipeline briefing', bot: "Created cron job. I'll check your pipelines every weekday at 9:00 AM and send you the results." },
  { label: 'Learn', user: 'no, always use the staging profile for deploy credentials', bot: "Learned: Use the staging profile for deploy credentials. I won't make this mistake again." },
  { label: 'Vision', user: '[pastes a screenshot of an error]', bot: "That's a NullPointerException in OrderService.java:142. The customer field is null when..." },
];

export const FAQ = [
  { q: 'What runs locally?', a: 'VibecodersCrew runs its gateway and dashboard locally. Model requests and calls to integrations that you enable leave your machine according to those providers\' policies, so review your configuration before connecting them.' },
  { q: 'How do I choose a model?', a: 'Connect a supported model provider during setup, then select the provider and model from your local configuration or dashboard.' },
  { q: 'Can non-engineers use it?', a: 'Yes — PMs, designers, data scientists, and any role. Configure the local dashboard or an optional channel integration for the workflow you need.' },
  { q: 'How do I add custom tools?', a: "Drop an MCP server config in ~/.kiro/crew/mcp.json. It's auto-discovered and synced. Or install via the dashboard MCP tab." },
  { q: 'How do I contribute?', a: 'Fork VibecodersCrew on GitHub, create a branch, and open a PR. See CONTRIBUTING.md for full guidelines.' },
];

export const THEMES = [
  '#22c55e', '#f59e0b', '#6366f1', '#f43f5e', '#06b6d4',
  '#a78bfa', '#88c0d0', '#e0af68', '#eb6f92', '#fab387',
  '#d4be98', '#f9e2af', '#93a1a1', '#7dcfff',
];
