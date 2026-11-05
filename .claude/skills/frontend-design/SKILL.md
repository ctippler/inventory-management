---
name: frontend-design
description: Redesign a Vue 3 application's UI into a modern SaaS-style interface - vertical navigation sidebar on the left instead of a top nav bar, slim sticky header, consistent spacing scale, polished card layouts. Use when asked to redesign, modernize or "make it look like a SaaS app", to move navigation into a sidebar, or to add a collapsible / icons-only sidebar.
---

# Frontend Design: SaaS-style Vue 3 redesign

Turn a top-nav Vue 3 app into a sidebar-based SaaS layout without touching
business logic. Shell and global styles change; views keep working unmodified.

## Ground rules

- **Shell first, views last.** Almost all of the redesign lives in the app shell
  (`App.vue` or the root layout) and its global stylesheet. Views should only
  need changes if they hard-code layout assumptions (sticky offsets, max-widths).
- **Respect the project's design system.** Read `CLAUDE.md` / `client/CLAUDE.md`
  for colors, "no emojis", chart conventions. In this repo: slate/gray
  (`#0f172a`, `#64748b`, `#e2e8f0`), status green/blue/yellow/red, custom SVG.
- **No new dependencies by default.** Icons are inline SVG in one small
  component; layout is CSS Grid/Flexbox; no UI kit.
- **Keep i18n intact.** Every visible string goes through the existing `t()`.
  Do not "fix" untranslated strings you didn't introduce unless asked — some
  are known bugs tracked elsewhere.
- **Composition API**, `setup()` returning bindings, scoped styles for new
  components, unique `:key`s — follow `client/CLAUDE.md`.

## Layout blueprint

```
┌──────────┬─────────────────────────────────────────┐
│  Brand   │  Header: section name     lang · profile│  sticky, 64px
│──────────│─────────────────────────────────────────│
│  Nav     │  FilterBar (if the app has global ones) │  sticky under header
│  items   │─────────────────────────────────────────│
│  (icon + │                                         │
│   label) │  <router-view />  max-width ~1440px     │
│          │                                         │
│──────────│                                         │
│ Collapse │                                         │
└──────────┴─────────────────────────────────────────┘
```

- Root: `display: grid; grid-template-columns: var(--sidebar-w) 1fr`.
- Sidebar: `position: sticky; top: 0; height: 100vh`, dark slate
  (`#0f172a`), text `#cbd5e1`, active item `#1e293b` background with a 3px blue
  (`#3b82f6`) left indicator and white text.
- Drive the nav from an array (`{ to, labelKey | label, icon }`) rendered with
  `v-for`, keyed by `to`. Active state via `router-link`'s `active-class` /
  `exact-active-class` (use exact for `/`).
- Header: white, bottom border `#e2e8f0`, holds language switcher and profile
  menu on the right. Dropdowns that opened downward from a top nav keep working.
- Anything that used to be `position: sticky; top: <old nav height>` must be
  moved to the new header height. Expose heights as CSS custom properties on
  `:root` (`--header-h`, `--sidebar-w`, `--sidebar-w-collapsed`) and use them.

## Visual system

| Token | Value |
|---|---|
| Spacing scale | 4 · 8 · 12 · 16 · 24 · 32 px (0.25–2rem) |
| Radius | 12px cards, 8px controls, 999px pills |
| Card | white, 1px `#e2e8f0` border, `0 1px 2px rgba(15,23,42,.04)` shadow; hover lift only on clickable cards |
| Page bg | `#f8fafc` |
| Text | headings `#0f172a`, body `#334155`, muted `#64748b` |
| Focus | `0 0 0 3px rgba(59,130,246,.25)` ring on every interactive element |

Cards: generous padding (20–24px), header row separated by a hairline, titles
600 weight ~1rem. Stat cards: label small caps-ish muted, value large and tight.
Tables: sticky-free, 12px vertical cell padding, muted uppercase 0.75rem headers,
row hover `#f8fafc`.

## Collapsible sidebar (icons-only mode)

- State in a tiny composable (`useSidebar`) so header/sidebar share it.
- Width toggles between `--sidebar-w` (240px) and `--sidebar-w-collapsed`
  (72px) with a `transition` on `grid-template-columns`.
- Collapsed: hide labels and brand text (keep the brand mark), center icons,
  give each link `:title` and `aria-label` so the label is still available as
  tooltip and to screen readers.
- Default: collapsed below 1024px (`matchMedia`), expanded otherwise. A manual
  toggle overrides and is remembered in `localStorage` — wrap every storage
  access in `try/catch`.
- Toggle button: `aria-expanded`, visible focus ring, chevron icon that flips.

## Workflow

1. Read the shell (`App.vue`, `main.js`, global CSS) and every component that
   sits in the old top nav. Note sticky offsets and max-widths.
2. Ask the user (AskUserQuestion) only what the code can't answer: sidebar
   color, where header widgets go, icon approach, whether views get restyled.
3. Build: icon component → sidebar composable → shell markup → global tokens
   and card/table polish → fix sticky offsets in child components.
4. Verify in the running app with Playwright MCP: every nav item routes and
   highlights, collapse toggle works, 1280px and 900px widths have no
   horizontal scroll, dropdowns (language, profile) still open, Japanese
   locale has no layout overflow, console has no new errors.
5. `npm run build` must pass.
