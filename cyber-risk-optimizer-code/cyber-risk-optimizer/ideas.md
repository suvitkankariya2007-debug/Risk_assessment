# Axiom Risk — Product UI Direction

## Three stylistic approaches

### Theme Name: Quiet Command Center
**Very Brief Intro:** A dark, high-trust operating environment that makes exposure, control performance, and capital allocation legible at a glance. It feels like a serious enterprise instrument rather than a marketing site.
**Probability:** 0.07

### Theme Name: Paper + Signal
**Very Brief Intro:** A warm editorial risk workspace where paper-toned surfaces and precise amber/teal markers turn complex cyber evidence into board-ready decisions. It balances human judgment with machine clarity.
**Probability:** 0.03

### Theme Name: Regulated Glasshouse
**Very Brief Intro:** A cool, pale institutional dashboard with translucent layers, restrained blue accents, and quiet compliance cues. It feels credible for regulated finance, healthcare, and public-sector buyers.
**Probability:** 0.08

## Selected approach: Quiet Command Center

### Design Movement
Neo-institutional software: the visual discipline of capital-markets terminals, modern control rooms, and premium enterprise workflow products, softened with editorial spacing and carefully chosen warmth.

### Core Principles
1. **Evidence before decoration.** Every visual treatment should reinforce provenance, confidence, or prioritisation.
2. **Exposure is the protagonist.** Translate technical conditions into business impact, especially expected loss and protected value.
3. **Calm under pressure.** Use one purposeful signal colour and avoid noisy alarm styling; risk states should be clear without shouting.
4. **Decisions, not dashboards.** The interface should make the next action and its economic rationale obvious.

### Color Philosophy
The foundation is deep ink navy, chosen because it gives the interface the gravity of a risk terminal and lets data marks breathe. Warm off-white is used for primary content surfaces to keep dense analysis approachable and readable. Oxidized amber is the ownable signal colour: it indicates decisions, active recommendations, and capital movement rather than generic danger. Teal marks protection and confidence. Red is reserved for true exposure deterioration, never used as ambient decoration.

### Layout Paradigm
A persistent left rail anchors the operating model while the main workspace uses a staggered, asymmetric analytical canvas: a wide hero metric plane, a narrow live-signal column, then an evidence row and a decision feed. Cards should not all share the same proportions; use a mix of a large narrative chart, compact metric tiles, and full-width tables to create hierarchy.

### Signature Elements
- **Exposure ribbon:** slim amber-to-teal progress strokes used to show how much modeled loss is being addressed by the proposed portfolio.
- **Signal rail:** small uppercase source labels such as `MODEL / CONTROL / THREAT` that make data provenance visible.
- **Decision trace:** short, timestamped rationale lines that show how a recommendation moved from signal to investment action.

### Interaction Philosophy
Interactions should feel like inspecting an instrument. Hovering reveals provenance and calculation context; selecting a risk surface updates the evidence trail; changing the budget scenario updates the recommendation copy and exposure ribbon with quick, low-drama motion. Destructive or high-impact actions should ask for confirmation. Structural navigation should stay instant and predictable.

### Animation
Use 160–220ms ease-out transitions for hover, focus, and active states. On initial load, reveal the hero plane first, then stagger supporting tiles by 50ms. Data strokes may animate once from left to right to establish direction, but never loop continuously. Avoid animating whole layouts or flashing risk states. Respect `prefers-reduced-motion` by removing entrance transforms and stroke animation while preserving state changes.

### Typography System
Use **Space Grotesk** for headlines, metric numerals, navigation labels, and compact tags: its slightly technical geometry gives the interface a distinct instrument-like voice. Use **DM Sans** for body copy, table content, and supporting descriptions so dense information remains open and comfortable. Headline hierarchy is compact and sentence-case; metric values are bold with tight tracking; labels are uppercase with generous letter spacing.

### Brand Essence
Axiom Risk is the decision layer for security leaders who need to quantify cyber exposure and allocate capital with confidence; it is different because it ties live control evidence to expected loss and investment outcomes.

Personality: **measured, forensic, decisive**.

### Brand Voice
Headlines should be direct and economically literate. CTAs should describe the decision being made, not a vague action. Microcopy should explain why a recommendation exists in one sentence and name the evidence behind it.

Example headline: **Put a rupee value on the unknown.**

Example CTA: **Review the ₹2.4Cr exposure gap**.

### Wordmark & Logo
The mark is a three-facet shield forming an upward chevron around a protected center, suggesting evidence converging into a decision. The wordmark should be set in a custom-spaced uppercase treatment of `AXIOM RISK`, with the symbol carrying the recognition load; do not use the brand name as a default logo font.

### Signature Brand Color
**Oxidized Amber — `#D8943B`**. It is less alarmist than red and more ownable than default blue; it signals the movement of capital toward a more defensible risk position.

## Product surface used for first delivery

The first delivery will be a single, responsive executive workspace with a persistent navigation rail and interactive demo states for:

- Portfolio overview: modeled annual loss, protected value, control health, and optimisation status.
- Exposure translation: technical risk translated into rupee-denominated business impact.
- Investment optimiser: scenario budget, recommended control moves, and marginal risk reduction.
- Live signals: threat freshness, control verification, and a decision trace that explains the recommendation.
- Evidence drawer: a compact detail view for the selected exposure item.

The UI will use clearly marked demo values so the experience is credible without pretending to be connected to production data.

## Style Decisions

The interface now uses white analytical surfaces with a restrained enterprise purple signal as the primary brand accent. High, moderate, critical, and verified states keep distinct semantic markers so purple does not erase risk meaning. The workspace follows the device preference through `prefers-color-scheme`: light mode is white/lilac and dark mode is deep plum with high-contrast analytical surfaces. Alignment favors stable card gutters, non-wrapping action groups, and deliberate mobile stacking over compressed desktop layouts.

## Reference ground truth: CyberRiskIQ executive overview

The provided screenshot is the visual source of truth for this revision. It shows a dense, dark executive-terminal workspace rather than a marketing dashboard. The composition is anchored by a narrow left rail with the product identity at the top, a company/workspace selector, command-center navigation, governance navigation, and a small synthetic-data status footer. A compact top bar carries the active workspace, breadcrumb, role switcher (`Executive`, `CISO`, `Analyst`), and a green live Monte Carlo status pill.

The main surface uses a near-black blue-grey background with thin low-contrast dividers, charcoal cards, muted grey body text, white headings, and a restrained muted-gold accent for currency, buttons, chart lines, progress bars, and active navigation states. Green is reserved for live/trending-down/positive states; red is reserved for worsening tail risk and new findings. The information hierarchy is intentionally dense and executive-facing: an eyebrow and headline, compact explanatory copy, two action buttons, four metric cards, then a two-column analytical grid.

The first analytical row contains a large `Risk exposure trend — org-wide EAL` area chart on the left and `Top 5 risk contributors` ranked bars on the right. The next row begins with an `Investment vs. Risk-Reduction curve` control with a visible budget amount and ends with a `Framework compliance snapshot` showing horizontal coverage bars. Cards use small corner radii, generous internal padding, uppercase monospace-like labels, and strong horizontal alignment. The new implementation should preserve the current prototype’s scenario controls and evidence drawer, but visually place them inside this reference structure.

Reference fidelity overrides the previous white-purple exploration for this revision. The primary target is an aligned dark executive overview at desktop widths with a responsive stacked layout and mobile drawer behavior at smaller widths.
