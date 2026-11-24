# DESIGN.md — Visual identity and UI standards

**Name:** EcoSort · **Line:** "Which bin? Know in a second." · **Direction:** *Field Instrument*. The UI should feel like a precise piece of equipment used by sanitation crews and municipal engineers: industrial, honest and data-first. It should **not** look like a generic AI startup template.

## 0. Research: how the industry's leaders present themselves (inspected live, Nov 2026)
| Company | Type | Colour | Shape / imagery | What we take |
|---|---|---|---|---|
| **Greyparrot** (greyparrot.ai) | **Lexend** 500 for everything; H1 56px, H2 40px | White pages, deep navy ink `#171726`, **one** crimson accent `#D7004E` | Square buttons (0 radius), **big stat numbers** (300+, 52bn+), real **dashboard screenshots** as hero visuals | One accent; stats as headlines; the product UI is the imagery |
| **AMP** (ampsortation.com) | **Ruder Plakat**: huge condensed UPPERCASE poster display (~155px). Body in **ABC Diatype** grotesk | Near-black `#212121` / off-white `#F2F2F2` | Full-bleed **real facility photography**, 0 radius, very large type | Condensed poster type for one moment per page; dark industrial sections |
| **Recycleye** (recycleye.com) | Geometric sans heading (600), Roboto body | Brand green `#53AE47` + deep teal `#0C3E4F` on white | **Small uppercase letter-spaced labels** above headings ("AI-POWERED SOLUTIONS"), square buttons with **↘ arrows** | Eyebrow labels; arrow CTAs |
| **TOMRA** (tomra.com) | **Proxima Nova** 600, H1 60px | Deep navy ink `#001A38`, orange `#D54300` accent | Breadcrumbs, large rounded photo/video, generous white space | Navy-ink text instead of black; calm hierarchy |

**What they all do:** one sans family (no serif display fonts), ink-coloured text (never pure `#000`), **exactly one** loud accent, near-square controls, real photos and product UI instead of illustrations, big numbers, and sparse copy.
**Where we differ:** they sell to plant operators; we serve a resident holding one item. So we keep their industrial precision, add a **"viewfinder + readout"** interaction at the centre, and use stream colours as functional signals.

## 1. Hard bans (the "no AI slop" list): the agent must not use any of these
- Fonts: Inter, Geist, Roboto, Poppins, Montserrat, and **any serif display font** (Fraunces, Playfair, Instrument Serif, DM Serif, etc.).
- Purple/indigo gradients, mesh or blob backgrounds, glassmorphism, neon glows, "aurora" effects.
- The sparkle ✨ "AI" icon, robot/brain illustrations, emoji used as icons, stock photos of people, 3D blobs.
- A centred hero with two pill buttons and a three-card icon grid below it; rounded-2xl cards with heavy shadows everywhere; every section in identical cards.
- Fake numbers, testimonials, "trusted by" logos, ™, "revolutionary" or "cutting-edge" copy.
- Lorem ipsum. Every string is real product copy.

## 2. Typography (all self-hosted with `next/font/google`; CSP `font-src 'self'`)
| Role | Font | Settings |
|---|---|---|
| Display (H1, hero stat numbers, result label) | **Archivo** (variable, `wdth` axis) | `font-stretch: 75%` (condensed), weight 700–800, UPPERCASE for the hero and result label only, letter-spacing −0.01em. Inspired by AMP's poster type, used **once per page** |
| Headings / UI / body | **Archivo** | `wdth 100`, weight 400 body / 500 UI / 600 H2–H3. One family keeps it coherent, as Greyparrot and TOMRA do |
| Data / eyebrows / readouts | **JetBrains Mono** | weight 500, tabular numbers. Eyebrows UPPERCASE, 12px, letter-spacing 0.08em (Recycleye-style labels, mono for an instrument feel) |

Scale (px): 12 · 14 · 16 · 18 · 22 · 28 · 40 · 56 · 88 (hero condensed) · 120 (desktop result label, condensed). Body 16/1.6, max 68ch. Headings use `text-wrap: balance`.

## 3. Colour tokens (`globals.css` via Tailwind v4 `@theme`)
**Brand accent = "Hi-Vis"**, the high-visibility yellow-green of sanitation-worker vests and AMP's site photos. It's our single loud accent (like Greyparrot's crimson) and it is **not** a stream colour, so it never clashes with the bin signals.

| Token | Light | Dark | Use |
|---|---|---|---|
| `--paper` | `#F3F2EC` | `#0B1210` | page background |
| `--surface` | `#FFFFFF` | `#121B18` | panels |
| `--ink` | `#0E1A16` | `#ECEFEA` | primary text (ink, never `#000`) |
| `--ink-2` | `#4A5650` | `#A3ADA7` | secondary text |
| `--rule` | `#D9D8CF` | `#24302B` | 1px hairlines (preferred over shadows) |
| `--hivis` | `#D4F23A` | `#D4F23A` | primary CTA fill (**with `--ink` text**), scan line, focus ring, active nav marker. Never used as text on light backgrounds (fails contrast) |
| `--panel-dark` | `#0E1A16` | `#060A09` | dark "instrument" sections (hero scanner, readout) |
| `--wet` | `#1E8E4E` | `#3FCB7E` | wet stream |
| `--dry` | `#1F5FD1` | `#6EA2FF` | dry stream |
| `--sanitary` | `#C25A12` | `#F2994A` | sanitary stream |
| `--special` | `#C0262D` | `#FF6B6B` | special care stream |
| `--caution` | `#9A6A00` | `#F5C451` | "uncertain" state |

- Green = wet and blue = dry follow the common Indian bin convention. The orange and red for sanitary and special care are **our UI choice**; the About page says so.
- **Never use colour alone:** every stream signal = colour chip + lucide icon (wet `Leaf`, dry `Package`, sanitary `ShieldAlert`, special care `TriangleAlert`) + text label.
- Contrast ≥ 4.5:1 for body text and ≥ 3:1 for large text and UI parts, in both themes. Checked by axe in Playwright.

## 4. Shape, rules and depth
- Radius: **2px** for buttons, inputs and chips; **4px** for images and panels. (The industry sites use 0; 2px softens slightly without going "bubbly".)
- Depth comes from **hairline rules and tone changes**, not shadows. At most one shadow token, for menus and popovers only.
- A grid of 12 columns, max 1240px, 24px gutters, and visible 1px column rules in the hero panel (very faint, like a measuring instrument's graticule).
- Section rhythm: 96px between sections on desktop, 64px on mobile. Every section starts with a mono eyebrow numbered like a spec sheet: `01 — SCAN`, `02 — STREAMS`, `03 — MODEL`.
- CTAs are rectangular, with text + arrow (`→` primary, `↗` external). Primary = Hi-Vis fill with ink text; secondary = 1px ink outline.

## 5. Signature components
1. **Viewfinder scanner** (the hero, on the dark panel)
   - A 4:3 drop zone with **four corner brackets** (camera viewfinder marks), not a dashed rounded box. Idle text in mono: `DROP PHOTO · PICK FILE · USE CAMERA`.
   - The camera opens inside the same frame (`getUserMedia`, `facingMode: "environment"`) with a shutter button.
   - While inferring, a **Hi-Vis scan line** sweeps top to bottom and a mono status ticks: `PREPROCESSING → CNN FORWARD PASS → GRAD-CAM`, all driven by real request state (not a fake timer). No sweep under `prefers-reduced-motion`.
   - Model selector as a segmented control: `WASTENET (FROM SCRATCH) | MOBILENETV3 | EFFICIENTNET-B0`.
2. **Readout panel** (result page): a spec-sheet layout
   - The label in condensed uppercase display (e.g. `PLASTIC`), then a large stream bar in the stream colour with icon and "DRY WASTE → Material Recovery Facility".
   - Confidence as a mono readout `0.91` with a 1px-rule meter, and a tick at the uncertain threshold.
   - Top-3 as horizontal hairline bars. Disposal steps numbered `01 02 03`.
   - Metadata row in mono: `MODEL efficientnet_b0 · 84 MS · ID 3f2a…`.
3. **Heatmap compare**: photo vs Grad-CAM overlay with a draggable vertical divider (keyboard: ←/→ moves 5%), plus a one-line caption on what the heatmap means.
4. **Specimen wall** (home, section 02): a dense grid of **real test-set photos** (12 classes × 2), each with a mono caption `ORGANIC · WET` and a "sample" tag. Clicking one runs it through the model. This is our version of using real product imagery.
5. **Four-stream legend**: four tall columns separated by hairline rules (not cards), each with a colour bar on top, icon, stream name, 4 example items and "where it goes". The SWM Rules 2026 context sits in a one-line mono note.
6. **Stat strip**: Greyparrot-style big numbers in condensed display: `18,951 TRAINING IMAGES · 12 MATERIALS · 4 STREAMS · {best test accuracy}%`. The accuracy comes **only** from `/api/v1/models`; if it's missing, the tile is hidden.
7. **Model page**: like an engineering report. A comparison table with hairline rows and mono numbers (the best value per column marked with a Hi-Vis dot), the confusion matrix as a square heatmap in ink-to-Hi-Vis tones (accent sequential), per-class F1 as horizontal bars, and training curves with thin 1.5px lines.
8. **Insights page**: a dark "control room" panel with KPI readouts at the top, then charts on paper. Stream charts use stream tokens; everything else uses ink tones + Hi-Vis for highlights only.

## 6. Page composition
- **Global nav:** wordmark left (`ECOSORT` in condensed display plus a 2×2 four-stream square mark); links `Scan · History · Insights · Model · About` in Archivo 500 with a Hi-Vis underline for the active route; a theme toggle on the right. Sticky, paper background with a bottom hairline.
- **`/` (home):**
  - (1) Dark instrument hero: left column = eyebrow `01 — SCAN`, H1 condensed uppercase "WHICH BIN?", one-line sub-copy and the SWM-2026 note; right/main = viewfinder scanner. Asymmetric 5/7 split, not centred.
  - (2) Specimen wall.
  - (3) Four-stream legend.
  - (4) "How it works" as a horizontal pipeline diagram drawn with rules: `PHOTO → RESIZE 224 → CNN → SOFTMAX → STREAM MAP → GRAD-CAM`, with the actual layer counts and params pulled from `/models`.
  - (5) Stat strip.
  - (6) Footer with dataset citations and an "academic project, non-commercial" note.
- **`/scan/[id]`:** 7/5 split: heatmap compare | readout panel. Feedback sits under the readout: "Correct?" `YES` / `NO → choose material` (a 12-option grid with stream chips).
- **`/history`:** a dense contact-sheet grid (square thumbs, mono captions, stream colour bar on the bottom edge), stream filter as segmented control, "Load more".
- **`/model`, `/insights`, `/about`:** as above. `/about` reads like a project report: problem, rules, data, method, limitations, references.

## 7. Motion
- 150–200ms `cubic-bezier(.2,.7,.2,1)` for hover and focus. Page transitions: none (fast is the aesthetic).
- Allowed moments: the scan-line sweep, readout numbers counting up once (≤ 400ms) on result load, and the heatmap divider easing on first reveal.
- Everything respects `prefers-reduced-motion: reduce`.

## 8. Imagery and icons
- Imagery = our own dataset photos (labelled "sample"), Grad-CAM outputs and real charts. No stock people, no AI-generated scenes.
- Icons: lucide-react at 1.5px stroke, 20px. No filled icon packs and no emoji.
- Logo: an SVG wordmark `ECOSORT` (Archivo 800, `wdth 75`) plus a mark made of four 2px-gapped squares in the stream colours (a 2×2 grid). Favicon = the mark alone.

## 9. Accessibility (WCAG 2.2 AA, verified by axe + Lighthouse)
- Visible focus: 2px Hi-Vis outline + 2px ink offset (works on light and dark). Skip link. Logical heading order.
- The scanner works fully without a camera; denied permission shows an inline message.
- Alt text: results "Photo classified as plastic (dry waste)"; heatmap "Model attention heatmap for plastic".
- Charts have a `<figcaption>` summary and a visually-hidden data table.
- Touch targets ≥ 44px. The divider slider has `role="slider"` with aria-valuenow.

## 10. Quality bar before any UI milestone is "done"
Take screenshots at 375, 768 and 1440 widths, in light and dark, of `/`, `/scan/[id]`, `/model` and `/insights`, and save them to `frontend/tests/screenshots/`. Review them against §1 bans and §5 components, and log the result in DECISION_LOG.md.
