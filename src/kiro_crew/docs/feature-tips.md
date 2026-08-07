<!-- Modified 2026 by Sereja Ris for VibecodersCrew (community fork of Kiro Crew). -->
<!-- See NOTICE and CHANGELOG.md for the nature of the modifications. -->
# Feature Tips

KiroCrew occasionally surfaces a small tip above the chat composer while the
agent is working, pointing at a feature you have not used yet. Tips come from
the local feature catalog and your local dismissal preferences. No activity
profile or background analytics is collected for tip selection.

## How It Works

- Tips appear only during a running turn, about 10 seconds in, as a single
  strip above the input box. They never cover chat content — the strip takes
  real layout space and pushes the conversation up.
- At most one tip is shown per turn, and after a tip is shown the next one
  waits for the cadence window (6 hours by default).
- Candidates come from the bundled feature catalog. Selection is local and
  weighted toward recently updated catalog entries, with an optional local
  exploration ratio for broader discovery.
- Tips never appear in temporary sessions, split view, or embedded
  composer-less views.

## Controls

Three layers, from one tip to everything:

| Action | Effect |
|--------|--------|
| Click the X on a tip | Permanently dismisses that tip (the feature, not just the wording) |
| Settings -> Chat -> Feature Tips | Per-user toggle; turns all tips off or back on |
| `dashboard.tips_enabled: false` in config | Instance-wide kill switch |

When the instance config disables tips, the Settings toggle is grayed out with
a note saying so.

## Privacy

Tip selection does not read chat memory, active projects, or recent activity.
The local tips state file is written with owner-only permissions. Temporary
sessions (which promise no memory reads) never show tips.

## Configuration

```yaml
dashboard:
  tips_enabled: true        # instance-wide switch
  tips_cadence_hours: 6     # minimum gap between tips
  tips_max_count: 5         # retained compatibility field; no model generation
```

See [Configuration Reference](configuration.md) for the full list.
