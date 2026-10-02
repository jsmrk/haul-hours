# Haul Hours Design System

Source: the user's "Design System Inspired by Kraken" message. This document applies that direction to the assessment application and supplements the [functional specification](2026-10-02-haul-hours-design.md). It defines implementation requirements; it does not change routing or duty calculations.

## Visual direction

White surfaces, near-black text, a cool neutral scale, and purple calls to action create a calm trip-planning workspace. Use the Haul Hours name throughout the application. Favor clear form labels, readable route details, and legible daily records over decorative content. Use restrained borders and the supplied subtle shadows to separate panels.

The initial application is a light theme. Dark mode is outside this design specification.

## Colors and token roles

| CSS token | Exact value | Use |
| --- | --- | --- |
| `--color-brand` | `#7132f5` | Primary CTA, links, selected controls, road route |
| `--color-brand-dark` | `#5741d8` | Outlined button text/border, primary hover |
| `--color-brand-deep` | `#5b1ecf` | Pressed primary state, strong selected accents |
| `--color-brand-subtle` | `rgba(133,91,251,0.16)` | Subtle purple surfaces and selected backgrounds |
| `--color-text` | `#101114` | Headings, body, entered values |
| `--color-neutral` | `#686b82` | Readable secondary text and labels |
| `--color-muted` | `#9497a9` | Inactive/decorative elements |
| `--color-surface` | `#ffffff` | Page, panels, inputs, sheets |
| `--color-border` | `#dedee5` | Dividers and panel borders |
| `--color-border-soft` | `rgba(104,107,130,0.24)` | Input and subtle component borders |
| `--color-neutral-subtle` | `rgba(104,107,130,0.12)` | Neutral badges |
| `--color-neutral-badge-text` | `#484b5e` | Neutral badge text |
| `--color-secondary-surface` | `rgba(148,151,169,0.08)` | Secondary button surface |
| `--color-success` | `#149e61` | Positive accents |
| `--color-success-subtle` | `rgba(20,158,97,0.16)` | Success badge surface |
| `--color-success-text` | `#026b3f` | Success badge text |

Use only the supplied purple scale. Error and blocked states use a clear icon, heading, explanation, and corrective action in readable text; they need no invented red palette. Pair every status color with a label or symbol. Green indicates a successfully generated result or positive action, rather than claiming that a parking space or regulatory certification has been verified.

Computed white-background contrast is approximately 6.04:1 for brand purple, 5.23:1 for cool gray, and 2.89:1 for silver blue. Use cool gray for ordinary secondary text and placeholders. Reserve silver blue for decorative or inactive content; important text needs at least 4.5:1 under the normal-text criterion. [W3C contrast guidance](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html)

## Typography

Display stack: `"Kraken-Brand", "IBM Plex Sans", Helvetica, Arial, sans-serif`.

Body stack: `"Kraken-Product", "Helvetica Neue", Helvetica, Arial, sans-serif`.

The supplied proprietary fonts are not bundled in the repository. Use these fallback stacks immediately. If licensed Kraken font files are provided, place them under `frontend/public/fonts/` and add local `@font-face` declarations with `font-display: swap`. Do not fetch proprietary font assets from Kraken's site. Font availability does not block the application.

| Role | Font stack | Size | Weight | Line height | Tracking |
| --- | --- | --- | --- | --- | --- |
| Hero | Display | 48px | 700 | 1.17 | -1px |
| Section | Display | 36px | 700 | 1.22 | -0.5px |
| Subheading | Display | 28px | 700 | 1.29 | -0.5px |
| Feature title | Body | 22px | 600 | 1.20 | normal |
| Body | Body | 16px | 400 | 1.38 | normal |
| Emphasized body | Body | 16px | 500 | 1.38 | normal |
| Button | Body | 16px | 500–600 | 1.38 | normal |
| Caption | Body | 14px | 400–700 | 1.43–1.71 | normal |
| Small | Body | 12px | 400–500 | 1.33 | normal |
| Decorative micro | Body | 7px | 500 | 1.00 | uppercase |

Use the 7px role only for nonessential decoration, if needed. Form labels, errors, timestamps, map legends, and log remarks remain readable at 14px or above; compact tick labels can use the 12px role. At mobile widths, reduce hero headings to the supplied 36px or 28px roles without shrinking body text.

## Components and states

Use locally generated shadcn/ui TypeScript components with the Radix base and Tailwind CSS v4. Customize their semantic CSS variables and component variants to this specification. Keep accessible keyboard, focus, and labeling behavior. Use Card for panels and Field for labeled inputs rather than parallel custom primitive components. Button corners are explicitly 12px; Card corners 16px; success/neutral Badge corners 6px/8px.

All button variants use a 12px radius, following the user's final "all buttons" rule. This resolves the earlier white-button example's 10px radius in favor of consistency. Never use pill-shaped buttons.

| Variant | Surface | Text/border | Spacing |
| --- | --- | --- | --- |
| Primary | Brand | White text | 13px vertical, 16px horizontal |
| Outlined | White | Dark purple text and 1px dark purple border | 13px vertical, 16px horizontal |
| Subtle | Purple subtle | Brand text | 8px internal padding; enlarge the hit area for standalone controls |
| White | White | Near-black text; subtle shadow | 13px vertical, 16px horizontal |
| Secondary | Secondary surface | Near-black text | 13px vertical, 16px horizontal |

Primary hover uses dark purple; pressed uses deep purple. Disabled controls preserve their labels and explain why submission is unavailable where necessary. Loading buttons include text such as "Planning trip…" and a small progress indicator. Icon-only controls require an accessible name. Use a minimum 44px interactive hit area for standalone buttons and map/list controls.

Focus treatment: 2px brand-purple outline with a 2px white offset. Inputs use white surfaces, 12px corners, the soft neutral border, 16px values, and persistent labels. Suggestions have a labeled keyboard selection state using the subtle purple surface. Validation messages sit next to the affected field, with an icon and readable text; preserve the entered value.

Panel radius is 16px; panel spacing uses 20px or 24px. Success badges use the supplied green surface/text and a 6px radius. Neutral badges use the supplied neutral surface/text and an 8px radius. Selected date tabs use subtle purple and brand text with a 12px radius.

Shadows: `--shadow-subtle: 0px 4px 24px rgba(0,0,0,0.03)` and `--shadow-micro: 0px 1px 4px rgba(16,24,40,0.04)`. Use borders as the primary separation mechanism; reserve elevation for popovers or interactive panels.

## Spacing and responsive layout

Spacing tokens, in px: `1, 2, 3, 4, 5, 6, 8, 10, 12, 13, 15, 16, 20, 24, 25`.

Radius tokens, in px: `3, 6, 8, 10, 12, 16, 9999`, plus `50%` for circular markers. The presence of the larger radius tokens does not permit pill buttons.

Breakpoints, in px: `375, 425, 640, 768, 1024, 1280, 1536`. Design mobile-first below 375 as well; these values mark adjustments, not minimum supported device widths.

| Width | Layout behavior |
| --- | --- |
| Below 375 / 375 | Single column; 16px page padding; full-width primary action; map above itinerary; 28px heading where necessary |
| 425 | Single column with 20px page padding and more comfortable optional-field spacing |
| 640 | 24px padding; paired optional fields and two-column summary cards where they fit |
| 768 | Date navigation and export controls can share a row; the form and full result remain stacked |
| 1024 | Trip form occupies a 320–380px left column; route/result workspace uses the remaining width; 24px gap |
| 1280 | Centered workspace up to 1280px wide; map and itinerary can sit side by side within the result column |
| 1536 | Retain the centered maximum content width, adding outer white space |

Do not force page-level horizontal scrolling. A daily log can use a clearly labeled internal scroll region and a full-sheet/print action on small screens; never compress its text to illegibility. Export/print uses a dedicated white sheet layout with repeating page headers and page breaks.

## Application placement

- Header: Haul Hours wordmark, a short purpose statement, and useful navigation to trip/results/logs. The purple CTA is "Plan trip".
- Form: the four required assessment fields first; departure and optional log metadata in an expandable section. Keep the primary action near validation feedback.
- Summary: clear mileage, drive time, elapsed time, pickup arrival, drop-off arrival, and delivery completion. Use typographic emphasis and labels rather than decoration.
- Map: purple route; current, pickup, and drop-off markers carry explicit symbols. Fuel, short break, daily rest, and restart markers use distinguishable icons and legends within the supplied palette. Map attribution stays visible.
- Itinerary: numbered events with duty code, time, duration, stop name, and reason. Selected event gets a subtle purple surface and a strong visible focus/selection outline.
- Logs: white sheets, near-black duty traces, cool-gray grid/labels, and explicit OFF/SB/D/ON rows. Purple may indicate the selected event in the interactive view. Print/PDF retains dark traces and labels for grayscale legibility.
- Empty/loading/blocked states: concise next-step guidance in the same panels. A blocked schedule displays its reason and safe prefix without a complete ETA or export action.

## Implementation and acceptance

Create `frontend/src/styles/{tokens.css,global.css}` during application foundation work. Apply reusable components under `frontend/src/components/ui/` during form work; feature components consume the tokens and shared controls. Keep the backend log graph neutral so presentation styling cannot alter its timestamps or mileage.

Verify the supplied colors, typography hierarchy, focus behavior, button radius, responsive layouts, and log legibility in actual browser flows. Check long location labels, open autocomplete menus, provider errors, and populated log sheets at the listed widths. Check that keyboard users can select locations and itinerary events, normal text has adequate contrast, and the exported record remains readable in grayscale. Final visual acceptance uses this document together with the functional specification.
