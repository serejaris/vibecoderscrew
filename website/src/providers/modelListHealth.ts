// Modified 2026 by Sereja Ris for VibecodersCrew (community fork of Kiro Crew).
// See NOTICE and CHANGELOG.md for the nature of the modifications.
// Tracks whether the model list currently served for a given provider came from
// a LIVE /api/models success or from a DEGRADED fallback (cached list or
// auto-only). UI mounts receive a static/cache catalog and never poll a
// provider; live entitlement discovery is an explicit action only.
//
// Keyed by provider id (read from the ['available-models', <providerId>] query
// key) so it is provider-safe. Default is "not degraded" (undefined → false):
// a provider whose adapter never marks itself only ever stops polling, so this
// remains useful to diagnostics and explicit refresh callers.

const degradedByProvider = new Map<string, boolean>()

/** Record whether the last fetch for a provider was degraded (fallback) or
 *  live. The adapter calls this on every fetch outcome. */
export function markModelsDegraded(providerId: string, degraded: boolean): void {
  degradedByProvider.set(providerId, degraded)
}

/** True only when the provider's last served list is known to be a degraded
 *  fallback. Unknown/never-fetched providers report false (not degraded). */
export function modelsDegraded(providerId: string): boolean {
  return degradedByProvider.get(providerId) === true
}

/**
 * Refetch cadence for model queries. Passive mounts must not re-enter
 * `/api/models` on a timer; the backend's default route is static/cache-only.
 */
export function modelListRefetchInterval(
  query: { queryKey: readonly unknown[] },
): number | false {
  void query
  return false
}
