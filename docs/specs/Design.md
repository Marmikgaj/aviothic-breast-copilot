# Design.md — Visual System

## 1. Overall Direction

Clinical, precise, trustworthy, calm under pressure. Reference aesthetics: RadAI, Epic MyChart provider portal, clean medical dashboards (e.g., Qure.ai). The interface should feel like a tool a radiologist trusts during a busy reading session — dense where it needs to be, never decorative.

Because v1 serves two distinct outputs (clinician dashboard vs. the patient-friendly summary a clinician shares), the system uses **one shared visual language with two density modes**:

- **Clinician View** — compact, data-dense, monospace for raw/structured data.
- **Patient Summary View** — same palette and type family, but larger type scale, more whitespace, shorter line lengths, and no raw JSON/monospace — this is a document meant to be read by a non-clinician.

## 2. Color Palette

| Role | Hex |
|---|---|
| Primary (deep trust blue) | `#1E3A5F` |
| Secondary (soft slate) | `#4A6572` |
| Accent — calm/success (clinical teal) | `#2A9D8F` |
| Accent — warning (amber) | `#E9C46A` |
| Background (main canvas) | `#F8F9FA` |
| Background (cards) | `#FFFFFF` |
| Text (body) | `#212529` |
| Text (secondary/muted) | `#6C757D` |
| Semantic — success | `#2A9D8F` |
| Semantic — warning | `#E9C46A` |
| Semantic — error | `#E76F51` |
| Semantic — info | `#457B9D` |

## 3. Typography

- **UI text:** Inter or Source Sans Pro
- **Extracted/raw JSON, structured data:** JetBrains Mono or Fira Code (Clinician View only — never used in the Patient Summary View)
- **Scale:** 12px captions → 28px page titles (Clinician View). Patient Summary View starts at 15px body minimum for readability.

## 4. Spacing & Sizing

- 8px base grid; padding in multiples of 8 (16, 24, 32)
- Clinician View: compact density for data-heavy screens
- Patient Summary View: generous spacing, wider line height, shorter measure (~60–70 characters per line)

## 5. Component Style Notes

- Subtle borders: 1px `#DEE2E6`
- No heavy shadows — clinical flatness
- 4px corner radius for cards
- Clear focus rings for keyboard navigation
- Button states have clear, distinct disabled styling
- Every AI-generated output (summary, chat answer) carries a persistent, non-dismissible "AI-assisted — not a diagnosis, review required" badge in the info color (`#457B9D`)

## 6. Dark Mode

Optional, for low-light reading rooms (Clinician View only — Patient Summary View is always light-mode, since it's meant to be printed/shared).
- Background: deep navy `#0D1B2A`
- High-contrast text
- Desaturated accent colors to reduce eye strain during long reading sessions

## 7. Accessibility Baseline

- WCAG 2.1 AA minimum
- 4.5:1 contrast ratios
- Visible focus states throughout
- Minimum 44px tap targets
- Screen-reader-friendly labels on all interactive elements
- Color is never the sole indicator of status — always paired with an icon and/or text label (critical for confidence flags on extracted entities)

## 8. Explicit Design Don'ts

- No playful illustrations or cartoon aesthetics
- No stock photos of smiling patients
- No gradient-heavy hero sections
- No neon or overly bright colors that cause fatigue during long reads
- No monospace/raw-JSON styling ever appearing in the Patient Summary View
