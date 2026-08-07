// Modified 2026 by Sereja Ris for VibecodersCrew (community fork of Kiro Crew).
// See NOTICE and CHANGELOG.md for the nature of the modifications.
import { describe, expect, it } from 'vitest'

import { codeBrowserBranchUrl, codeBrowserCommitUrl } from './codeBrowser'

describe('codeBrowser URL helpers', () => {
  it('builds a branch tree URL', () => {
    expect(codeBrowserBranchUrl('main')).toBe(
      'https://github.com/serejaris/vibecoderscrew/tree/main',
    )
  })

  it('keeps slashes literal in a branch ref (feat/foo)', () => {
    expect(codeBrowserBranchUrl('feat/foo')).toBe(
      'https://github.com/serejaris/vibecoderscrew/tree/feat/foo',
    )
  })

  it('escapes unsafe chars (space) while preserving the path', () => {
    expect(codeBrowserBranchUrl('wip branch')).toBe(
      'https://github.com/serejaris/vibecoderscrew/tree/wip%20branch',
    )
  })

  it('builds a commit URL from a short SHA', () => {
    expect(codeBrowserCommitUrl('9866ae7a')).toBe(
      'https://github.com/serejaris/vibecoderscrew/commit/9866ae7a',
    )
  })
})
