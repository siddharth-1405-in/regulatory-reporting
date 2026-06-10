# Handoff · Auditor Cockpit (Revenue Assurance)

A single-screen executive cockpit for the **Head of Internal Audit** to monitor the agentic Revenue Assurance platform in one place — variances by domain, AI-clustered exceptions, SLA tracking, a live AI insight stream, a dashboard chat, and a drafted month-end narrative.

> **About these files:** the HTML in this bundle is a **design reference** built to communicate intended look, density, and behaviour. It is not the production codebase. Your job is to **recreate it inside the target Revenue Assurance app** (Next.js 15 / React per the project's existing stack — see *Stack* below), using its existing component library and design tokens. Treat the HTML as the visual & interaction contract; treat this README as the implementation contract.

---

## 1. Fidelity

**High-fidelity.** Final colors, type, spacing, density, and live behaviours are all locked in the HTML. The developer should match the mock pixel-for-pixel — within the constraints of the chosen component library (shadcn/ui) — and then wire it to real data.

---

## 2. Stack (target codebase)

Per the project's existing slides (`Revenue Assurance Solution.html`, slide 8 "Implementation Plan"):

| Layer       | Choice |
|-------------|---|
| Framework   | **Next.js 15 (App Router)** + React 18 |
| Styling     | **Tailwind CSS** + `tailwindcss-animate` |
| Components  | **shadcn/ui** primitives (Card, Tabs, Button, Badge, Tooltip, Avatar, ScrollArea) |
| Charts      | **Recharts** for variance bars; tiny SVG sparklines hand-rolled |
| Icons       | **lucide-react** (use sparingly — design uses very few icons) |
| Fonts       | `next/font/google` — Montserrat (display) + Inter (body) |
| Data        | Next.js Server Actions or **tRPC**; **Postgres** behind it |
| AI          | **Anthropic Claude** via `@anthropic-ai/sdk` for narrative, insights, chat |
| Auth        | Project's existing auth (NextAuth or Clerk) — gate on role `AUDIT_HEAD` |
| Realtime    | **Server-Sent Events** for the chat stream and the insights ticker; polling every 60 s for KPI/refresh-timer |

Folder layout suggestion:

```
app/
  (cockpit)/
    cockpit/
      page.tsx                 // server component, fetches initial snapshot
      _components/
        TopBar.tsx
        ContextBar.tsx
        KpiStrip.tsx
        VariancePanel.tsx
        ClusteringPanel.tsx
        SlaPanel.tsx
        InsightsPanel.tsx      // SSE-subscribed
        ChatPanel.tsx          // SSE-subscribed
        NarrativePanel.tsx
      _hooks/
        useLiveInsights.ts
        useChatStream.ts
      _lib/
        formatINR.ts           // "₹42.7 Cr" / "₹1.3 Cr at risk"
        formatAge.ts           // "13d", "12d", "10d"
  api/
    cockpit/snapshot/route.ts  // GET — bundles every panel's data in one trip
    cockpit/insights/stream    // SSE
    cockpit/chat/stream        // SSE
    cockpit/narrative/route.ts // POST — regenerate
```

---

## 3. Page-level layout

A fixed **1440 × 1120** design canvas, centered on viewport and uniformly scaled with CSS `transform: scale()` (the prototype's `fit()` function). On desktop ≥ 1440×1120 it renders 1:1; on smaller viewports the whole canvas shrinks. Mobile is **out of scope** — IA Head uses this from a desk.

```
┌─────────────────────────────────── Top Bar (60px) ───────────────────────────────────┐
├──────────────────────────────── Context Bar (~58px) ─────────────────────────────────┤
│ ┌──────────────────────────────────────────────┐ ┌─────────────────────────────────┐ │
│ │            KPI STRIP  (90px, 6 cards)        │ │                                 │ │
│ ├──────────────────────────────────────────────┤ │                                 │ │
│ │                                              │ │     LIVE AI INSIGHTS            │ │
│ │           VARIANCE PANEL (250px)             │ │     (spans rows 2–3,            │ │
│ │           Computed vs Charged · by domain    │ │      320×~528)                  │ │
│ │                                              │ │                                 │ │
│ ├──────────────────────────────────────────────┤ │                                 │ │
│ │                                              │ │                                 │ │
│ │           AGENTIC CLUSTERING (268px)         │ │                                 │ │
│ │           Root-cause clusters by domain      │ │                                 │ │
│ │                                              │ │                                 │ │
│ ├──────────────────────────────────────────────┤ ├─────────────────────────────────┤ │
│ │           SLA TRACKING (168px)               │ │     DASHBOARD CHAT (168px)      │ │
│ │           Aging + Imminent breaches          │ │     Composer + suggestions      │ │
│ ├──────────────────────────────────────────────┴─┴─────────────────────────────────┤ │
│ │                  MONTH-END NARRATIVE  (1fr ~220px, full width)                    │ │
│ │                  Executive summary draft + side stats + actions                   │ │
└───────────────────────────────────────────────────────────────────────────────────────┘
```

CSS grid (from `Auditor Cockpit.html`, simplified):

```css
.main {
  display: grid;
  grid-template-columns: 1fr 320px;
  grid-template-rows: 90px 250px 268px 168px 1fr;
  gap: 10px;
  padding: 12px 22px 14px;
}
.kpi-strip       { grid-column: 1 / -1; grid-row: 1; }
.var-panel       { grid-column: 1 / 2;  grid-row: 2; }
.insights-panel  { grid-column: 2 / 3;  grid-row: 2 / 4; }
.clusters-panel  { grid-column: 1 / 2;  grid-row: 3; }
.sla-panel       { grid-column: 1 / 2;  grid-row: 4; }
.chat-panel      { grid-column: 2 / 3;  grid-row: 4; }
.narr-panel      { grid-column: 1 / -1; grid-row: 5; }
```

---

## 4. Design tokens

The project already ships these in `colors_and_type.css`. Mirror them into Tailwind's `theme.extend`:

### Colors

| Token              | Hex      | Role |
|--------------------|----------|---|
| `--uq-purple`      | `#492079` | Primary brand. KPI accents, panel titles. |
| `--uq-magenta`     | `#B31E7C` | Secondary accent. Eyebrows, "AI" tags, variance values, ▲ deltas. |
| `--uq-dark-purple` | `#3B2162` | Hero KPI background, brand text. |
| `--uq-lavender`    | `#A28BBD` | Mid-tone strokes, dark-bg supporting text. |
| `--uq-mauve`       | `#C879AB` | Tertiary accent (Treasury tag, fills inside dark cards). |
| `--uq-light-lavender` | `#E1D9EB` | Card fill (lavender). |
| `--uq-blush`       | `#EED8E6` | Warm card fill. |
| `--uq-near-white`  | `#FAFAFA` | Neutral fill. |
| `--uq-alt-light`   | `#F5F0FA` | Alt row. |
| Cockpit bg         | `#FBF9FD` | The dashboard canvas (between cards). |
| Border             | `#ECE4F2` / `#F0E8F6` | Panel borders + dividers. |
| Text dark          | `#333333` | Body. |
| Text mid           | `#555555` | Secondary. |
| Text muted         | `#666666` | Captions. |
| **Status — OK**    | `#1F8A5B` | "Live" dot, coverage green, recovery good. |
| **Status — Warn**  | `#E5A82C` / `#E27A2A` | 4–7 day SLA bucket, "warn" age badges. |
| **Status — Critical** | `#C03A3A` | 8–14 day bucket, ▼ negative deltas, breach dot. |

### Typography

```ts
fontFamily: {
  display: ['Montserrat', 'Arial Black', 'sans-serif'],  // 400-900
  body:    ['Inter', 'system-ui', 'sans-serif'],         // 300-700
  mono:    ['ui-monospace', 'SF Mono', 'Menlo'],
}
```

| Use                         | Family   | Weight | Size  | Letter-spacing | Casing |
|-----------------------------|----------|--------|-------|----------------|--------|
| Page title ("Auditor Cockpit") | display | 800 | 20px | -0.015em | normal |
| Panel title                 | display  | 800    | 14px  | -0.01em        | normal |
| Eyebrow / section label     | display  | 800    | 9–10px | .14–.18em     | UPPER |
| KPI value                   | display  | 800    | 26px  | -0.02em        | normal |
| KPI label                   | display  | 700    | 9.5px | .12em          | UPPER |
| Cluster name                | display  | 800    | 12px  | -             | normal |
| Body                        | body     | 400    | 11px  | -              | normal |
| Mono (timestamps, IDs)      | mono     | 400-700 | 9–10px | .02em        | normal |
| AI "tool" chip              | display  | 800    | 8.5px | .10em          | UPPER |

### Spacing & shape

| Token       | Value |
|-------------|-------|
| Card radius | `14px` panels, `10px` insight/breach rows, `9px` clusters & SLA buckets |
| Pill radius | `999px` |
| Panel padding | `14px` |
| Inner row padding | `7–10px` |
| Panel gap (grid) | `10px` |
| Card shadow | `0 1px 3px rgba(73,32,121,.06), 0 8px 20px rgba(73,32,121,.04)` |
| Card border | `1px solid #F0E8F6` |

### Stripes (variance "gap" pattern)

`repeating-linear-gradient(45deg, rgba(179,30,124,.22) 0 5px, rgba(179,30,124,.08) 5px 10px)`

---

## 5. Panels — section by section

### 5.1 Top Bar (60px, white, with gradient under-stroke)

**Left:** logo tile (34×34, `linear-gradient(135deg, #3B2162, #492079, #B31E7C)`, "UQ"), brand text `Uniqus · Revenue Assurance` + sub `Agentic Audit Platform`, vertical divider, breadcrumb `Audit Programs › Revenue Assurance › Auditor Cockpit` (last segment purple, others muted).

**Right:** period segmented control (FY26 / **Q1 FY26 (active)** / Apr 2026 / This Week), domain filter pill `● All Domains 5` with pulsing magenta dot, two icon buttons (⌥ command palette, ◐ theme toggle — both stubs), user pill (avatar gradient, "Priya Menon · Head of Internal Audit").

**Under-stroke:** 2px gradient bar `linear-gradient(90deg, #3B2162 0%, #492079 35%, #B31E7C 70%, #C879AB 100%)`.

**Data:**
- `currentPeriod` (one of `FY26 | Q1 | M | W`), default Q1
- `domains: string[]` selected (default all 5)
- `user: { name, role }` from auth
- Period control updates the `?period=` query param and refetches `/api/cockpit/snapshot`.

### 5.2 Context Bar (~58px, white, fixed below top bar)

Left side: eyebrow `INTERNAL AUDIT · REVENUE ASSURANCE` + `Auditor Cockpit` (h1). Then five **ctx-stat** units separated by 1px vertical dividers:

| Label                     | Sample value       | Source |
|---------------------------|--------------------|---|
| Period                    | `Apr 01 → Apr 28, 2026` | derived from period selector |
| Charges under audit       | `37 rules`         | `count(rules where status='active')` |
| Transactions analysed     | `142.6 M`          | `sum(transactions_processed)` for period |
| Coverage                  | `98.4 %` (green)   | `analysed / total_in_scope` |
| Last refresh              | `07 sec ago` (magenta, **live**, increments every 1 s) | `Date.now() - lastSnapshotAt` |

Right side: pill `● Live · streaming` (green) — driven by SSE connection state.

### 5.3 KPI Strip — 6 cards (`grid-template-columns: repeat(6, 1fr)`)

All KPIs **count up from 0** on mount (1.1 s, cubic-ease-out). Use `framer-motion` `useMotionValue` + `animate()`.

| # | Card variant      | Label                          | Sample value        | Footer                                     |
|---|-------------------|--------------------------------|---------------------|---------------------------------------------|
| 1 | `dark` (hero)     | Revenue Leakage Detected       | `₹42.7 Cr`          | `▲ 18.4% vs Mar` · `YTD ₹186 Cr` · sparkline top-right |
| 2 | `acc` (magenta)   | Recovered / Adjusted           | `₹27.3 Cr`          | `63.9% of detected` · `+₹4.1 Cr this wk`  |
| 3 | `warn`            | Open Exceptions                | `2,847`             | `↔ stable` · `₹15.4 Cr at risk`           |
| 4 | `acc`             | SLA Compliance · 14-day        | `87.2 %`            | `▼ 3.1 pp vs target` · `Target 90%`       |
| 5 | default purple    | High-Materiality Clusters      | `14`                | `3 new` · `≥ ₹1 Cr impact`                |
| 6 | `ok` (green)      | Audit Coverage                 | `98.4 %`            | `All rules green` · `1 rule paused`       |

Hero card has 22px-tall mini area chart (last 9 weeks of detected leakage) drawn as inline SVG; data shape `{ w: 'YYYY-Www', value: number }[]`.

**Color rules for change chips (`.kpi .ch`):**
- `▲` good (e.g. recovery up) → green
- `▲` bad (leakage up, breach up) → still green if it's the magenta hero (signals magnitude, not goodness — matches mock), but `▼ 3.1 pp vs target` is **red**: use `.ch.dn`
- Neutral `↔ stable` → magenta `.ch.fl`

### 5.4 Variance Panel — Computed vs Charged by domain

Five rows (Cards / Lending / Trade Finance / Treasury / Transaction Banking).

Each row is a 4-col grid `140px 1fr 90px 70px`:
1. Domain name (display 800 12px) + source system caption (10px muted).
2. **Stacked bar** (22px tall, radius 6, bg `#F4EEFA`):
   - `.charged` segment — solid `linear-gradient(90deg,#C9B8DC,#A28BBD)`, width = `charged / maxRevenue` × 100%.
   - `.gap` segment — repeating-stripe magenta, width = `(computed-charged)/maxRevenue` × 100%, starts at `charged%`.
   - `.computed` marker — 2px dashed magenta vertical line at `computed%`.
3. Variance value (display 800 13px magenta, label `VARIANCE` above in 9px muted).
4. Variance % (display 800 11px purple, ▲ arrow red if positive).

Footer legend with swatches + summary line `Total variance · ₹42.7 Cr across 5 domains · 2,847 exceptions`.

**Toolbar buttons (right of panel header):** segmented `Value` (default) | `% Variance` | `Count`, plus `Export` (CSV).

**Data API** — `GET /api/cockpit/variance?period=Q1`:
```ts
{
  metric: 'value' | 'pct' | 'count',
  maxRevenue: number,            // for bar scaling
  rows: {
    domain: 'Cards' | 'Lending' | 'TradeFinance' | 'Treasury' | 'TransactionBanking',
    sourceSystem: string,         // "VisionPlus · CardPro"
    charged: number,              // INR
    computed: number,             // INR
    variance: number,             // computed - charged
    variancePct: number,
    exceptions: number,
  }[],
  totals: { variance, exceptions, domains: 5 },
}
```

### 5.5 Agentic Clustering Panel

**Domain tabs:** `All domains (14) | Cards (5) | Lending (3) | Trade Finance (3) | Treasury (2) | Transaction Banking (1)`. Counts come from clusters grouped by domain. Active tab uses white bg + purple border + magenta count pill.

**Sort buttons** (header right): `Impact` (default) | `Confidence` | `Age`.

**Cluster card** — grid `38px 1fr 110px 80px 70px 30px`:
1. **Materiality tile** (34×34, gradient, `A1`–`A5` label). Tier determines gradient: `t1 magenta→darkpurple` (top materiality), `t2 mauve→purple`, `t3 lavender→darkpurple`, `t4 lavender→purple`.
2. **Body** — cluster name (12px display 800 dark-purple), then description (10px muted, **root-cause bold-magenta**).
3. Exception count (display 800 10.5px purple, label `EXCEPTIONS`).
4. ₹ Impact (display 800 12px magenta, label `IMPACT`).
5. Confidence (60×5 bar `linear-gradient(90deg, #492079, #B31E7C)`, label `CONFIDENCE`).
6. `›` arrow → drills to `/cockpit/clusters/[id]`.

Initial seed (5 clusters from the mock; in production these come from the clustering agent):

| id | domain | name | exceptions | impact_inr | confidence | tier | root_cause |
|----|--------|------|-----------|-----------|-----------|------|------------|
| A1 | Cards  | Annual fee at old rate (Feb-2026 repricing miss) | 380 | 24_000_000 | 0.96 | 1 | Billing engine config not migrated to circular FY26-09 |
| A2 | TradeFinance | LC commission slab cap applied a tier early | 62 | 31_000_000 | 0.91 | 1 | Rate-card lookup truncating tier at ₹49.99 Cr |
| A3 | Lending | FX markup using spot instead of TT rate | 412 | 18_000_000 | 0.88 | 2 | SWIFT charge rule reading mid-rate; policy FX-2024-07 specifies TT |
| A4 | Cards  | FX markup not applied on cross-border POS < ₹10K | 2140 | 14_200_000 | 0.82 | 3 | Legacy threshold from FY22 still hard-coded in VisionPlus |
| A5 | Treasury | NDF reset-day pricing using next-day fix | 28 | 9_400_000 | 0.78 | 1 | Calendar mapping skipping Mumbai holiday on Apr 14 |

**API** — `GET /api/cockpit/clusters?domain=all&sort=impact&limit=5`:
```ts
{
  totals: { all: 14, byDomain: Record<Domain, number> },
  clusters: {
    id: string, domain: Domain, name: string, description: string,
    exceptions: number, impactInr: number, confidence: number,
    tier: 1 | 2 | 3 | 4, rootCause: string, createdAt: ISODate, status: 'open' | 'in_review' | 'resolved',
  }[],
}
```

### 5.6 SLA Tracking Panel

Two halves side-by-side (`1fr 1fr`).

**Left — aging buckets** (4-col grid):

| Bucket    | Color top accent | Sample count | Sample value | Tail text |
|-----------|------------------|--------------|--------------|-----------|
| `0–3 d`   | green `#1F8A5B`  | 1,284        | `₹6.8 Cr`    | `in SLA`  |
| `4–7 d`   | yellow `#E5A82C` | 982          | `₹4.2 Cr`    | `watch`   |
| `8–14 d`  | red `#C03A3A`    | 468          | `₹3.1 Cr`    | `near breach` |
| `> 14 d`  | magenta `#B31E7C` | 113         | `₹1.3 Cr`    | `breached` |

Count uses display 800 22px dark-purple (magenta on breached bucket); tail uses display 700 10px mid.

**Right — Imminent breaches** card with red pulsing dot title `Imminent breaches · escalate today`. Each row is a 5-col flex:

```
EXC-ID (mono purple)  ·  description (text-dark, domain bold)  ·  owner (10px upper muted)  ·  age badge (display 800 white-on-red, "warn" variant = amber)
```

Seed rows: `EXC-8841 Cards · Annual fee miss · awaiting Product Owner sign-off · R. Shah · 13d (red)`, `EXC-8729 Trade Fin. · LC slab dispute · clarification requested · P. Iyer · 12d (red)`, `EXC-8702 Lending · Processing fee waiver outside policy · M. Khan · 10d (amber)`, `EXC-8688 Treasury · NDF reset variance · ops review · S. Rao · 9d (amber)`.

**API** — `GET /api/cockpit/sla?period=Q1`:
```ts
{
  buckets: { range: '0-3'|'4-7'|'8-14'|'>14', count: number, valueInr: number }[],
  imminent: { id, domain, summary, ownerName, ageDays, status: 'breached'|'warn' }[],
}
```

### 5.7 Live AI Insights (right column, spans rows 2–3)

A vertically stacked stream of **4 insight cards**. New cards are prepended every ~9 s (in production, pushed via SSE). When 5 exist, oldest is removed.

**Card layout:**
- Top row: domain tag (8.5px display 800 white on domain-coloured pill — see palette in 5.4) + timestamp (`just now`, `2 min ago`, ... — mono 9px right-aligned).
- Body (11px text-dark, line-height 1.4): one sentence; **subject and figures bold dark-purple**.
- Footer meta (9px display 700 muted): materiality `₹X.X Cr` · delta (`▲ 18.0%` red on bad, `▼ 4.2%` green on good, `▲ new` magenta for new clusters).

**Bottom of panel:** "Next refresh" progress bar — 3px height, fills `linear-gradient(magenta→mauve)` over 18 s, loops.

**SSE endpoint** — `GET /api/cockpit/insights/stream`:

```
event: insight
data: { "id":"ins_01H...","domain":"Cards","tag":"cards","headlineHtml":"<b>Cards leakage up 18%</b> month-on-month — driven by <b>annual fee not yet repriced</b> on 380 corporate cards after the Feb circular.","materialityInr":24000000,"deltaPct":18.0,"deltaDirection":"up_bad","createdAt":"2026-04-28T10:14:00Z" }
```

Client formats `createdAt` to a relative "X min ago" string and updates the relative-time labels every minute.

**Insight generation (backend):** every 6 hours an LLM job runs over the last 24 h of variance data and produces 3–5 one-liners with this Claude prompt skeleton:

```
You are the Live AI Insights agent for an Internal Audit head's cockpit. You see
the last 24 hours of: (a) variance deltas by audit domain, (b) newly opened
clusters, (c) SLA breaches. Produce 3-5 insights, each one sentence,
≤ 24 words. Lead with the subject in bold. Cite one specific number. Skip
anything below ₹0.1 Cr materiality unless it's a recovery / resolved event.
Return JSON: [{ domain, headlineHtml, materialityInr, deltaPct, deltaDirection }]
```

Insights are persisted to `live_insights` table and the latest 4 are seeded on page load so the panel isn't empty before SSE kicks in.

### 5.8 Dashboard Chat (right column, row 4)

Compact ChatGPT-style panel.

- Message list (gap 7, max 88% width).
  - User: magenta-purple gradient bg, white text, right-aligned, `border-bottom-right-radius: 3px`.
  - Assistant: `#F4EEFA` bg, dark text, left-aligned, `border-bottom-left-radius: 3px`.
- **Tool-call indicators** inside assistant messages, inline at the top of the bubble: white pill with `1px solid #E0CEE9`, magenta display 800 8.5px label, e.g. `Tool · variance.query`, `Tool · cluster.lookup`, `Tool · sla.lookup`, `Tool · owner.fetch`. These render in real-time as Claude makes tool calls; show 1–3.
- **Citations** at end of assistant text: `<sup>` style mono chips referencing cluster id / exception id / policy id (e.g. `A1`, `EXC-8841`, `FY26-09`). Clicking opens the source.
- **Typing indicator** while streaming: 3 bouncing dots in a `#F4EEFA` pill.
- **Composer:** rounded 10 input + magenta-purple gradient `Ask ↵` button. Placeholder rotates every 5 s through:
  - "Show me Trade Finance exceptions > ₹50L this month…"
  - "Why is the Cards backlog growing?"
  - "Recovery rate by domain for April?"
  - "Which exceptions breach SLA in the next 24 hours?"
- **Suggestion pills below composer:** `Top 5 leakage drivers`, `Recovery rate by domain`, `SLA breaches today` — clicking fills the composer.

**Tools the chat agent exposes (server-side):**

| Tool name           | Args                                    | Returns |
|---------------------|-----------------------------------------|---|
| `variance.query`    | `{ domain?, period, metric }`            | rows like 5.4 |
| `cluster.lookup`    | `{ id }` or `{ domain, topN }`           | cluster row(s) |
| `exception.search`  | `{ filters: { domain?, minValueInr?, ageGtDays?, ownerId? } }` | exceptions list |
| `sla.lookup`        | `{ bucket?, ownerId? }`                  | buckets / breach list |
| `owner.fetch`       | `{ entity, entityId }`                   | owner profile |
| `policy.lookup`     | `{ policyId }`                           | policy citation |

Backend pattern: `POST /api/cockpit/chat/stream` (SSE), `messages: [...]`. Use Anthropic's tool use loop, stream deltas as `event: token` and tool calls as `event: tool`. Persist chat in `chat_sessions` keyed by user.

### 5.9 Month-End Narrative (full-width footer)

Two-column grid `1fr 280px`.

**Left — narrative body** (lavender-fade bg, 3px magenta-purple gradient bar on the left edge):
- Phase line: `Section · Executive summary` (magenta eyebrow) and right-aligned `v3 · 92% confidence · 14 citations` (muted).
- H3 `April 2026 · Revenue Assurance — Executive summary` (display 800 14px dark-purple).
- 2 paragraphs (11px text-dark, line-height 1.55). **Subjects, figures, cluster IDs are bold dark-purple; headline ₹ amounts are magenta**. Inline citations look like `<sup class="cite">A1</sup>` — white pill, mono 9px, purple text, 1px lavender border.
- **Blinking caret** at the end of the in-progress sentence — animates `opacity` 1→0 at 1 s interval (`@keyframes blink`).

Header actions: `Drafted by Narrative agent · 3 min ago` eyebrow, then `Regenerate` | `Edit` (active) | `Send to Audit Committee` mini-buttons.

**Right — side stats stack** (3 cards + 2 action buttons):

| Card                  | Value                | Note |
|----------------------|----------------------|---|
| Recovery rate · Apr  | `63.9 %` (green)     | `Target 60% · +3.9 pp` |
| New rules deployed   | `7`                  | `3 Rule-Author drafts under review` |
| Estimated Q1 leakage | `₹118 Cr` (magenta)  | `Linear forecast · 92% CI ±₹6 Cr` |

Then `Preview PDF` (white, purple text) and `Approve draft` (gradient magenta-purple, white).

**Narrative generation:**
- `POST /api/cockpit/narrative/generate` — runs nightly on day-of-month-end and on demand.
- Uses Claude (haiku for speed) to draft from the snapshot. Streams tokens. Saves to `monthly_narratives` versioned per period.
- Citations rendered from a `citations` map the model emits: `{ "A1": { type: "cluster", id: "A1" }, "FY26-09": { type:"policy", id:"FY26-09" } }`.

---

## 6. Live behaviours / animations

| Element | Behaviour | Implementation |
|---|---|---|
| KPI counters | `0 → target` over 1.1 s, ease-out-cubic, on mount | `framer-motion`'s `animate()` with `useMotionValue` |
| `Last refresh` clock | Increments every 1 s, format `NN sec ago` → `N min NN sec ago` after 60 | `setInterval` + `useState` |
| `Live · streaming` dot | 1.4 s pulse halo | CSS `@keyframes pulse-g` |
| Insight stream | Prepend new card every 9 s, fade-in `slidein` (.6 s, translateY 6) | `setInterval` in dev; SSE in prod |
| `Next refresh` bar | 18 s fill, infinite loop | CSS `@keyframes fill` |
| Chat typing | 3 bouncing dots, 1 s loop | CSS `@keyframes typing` |
| Chat stream | Token-by-token append, tool pills slide in as tools fire | SSE events |
| Narrative caret | 1 s blink at end of streaming sentence | CSS `@keyframes blink` |
| Domain filter pill dot | 1.8 s pulse halo (magenta) | CSS `@keyframes pulse` |
| Imminent-breach dot | 1.4 s pulse halo (red) | CSS `@keyframes pulse-r` |

---

## 7. Domain model (Postgres / Prisma)

```prisma
enum AuditDomain { CARDS LENDING TRADE_FINANCE TREASURY TRANSACTION_BANKING }

model Rule {
  id           String       @id
  domain       AuditDomain
  name         String
  expression   String       // SQL or DSL
  status       RuleStatus
  policy       String?      // citation id, e.g. "FY26-09"
}

model Exception {
  id             String       @id           // "EXC-8841"
  domain         AuditDomain
  ruleId         String
  txnRef         String
  computedInr    Decimal
  chargedInr     Decimal
  varianceInr    Decimal
  clusterId      String?
  ownerEmpId     String?
  status         ExceptionStatus            // open | in_review | adjusted | recovered | disputed
  openedAt       DateTime
  closedAt       DateTime?
  slaDueAt       DateTime
}

model Cluster {
  id             String       @id           // "A1"
  domain         AuditDomain
  name           String
  description    String
  rootCause      String
  tier           Int
  confidence     Float
  exceptions     Exception[]
  createdAt      DateTime
  status         ClusterStatus
}

model LiveInsight {
  id             String       @id
  domain         AuditDomain
  headlineHtml   String
  materialityInr Decimal
  deltaPct       Float
  deltaDirection String                     // "up_bad" | "up_good" | "down_bad" | "down_good" | "flat" | "new"
  createdAt      DateTime
}

model MonthlyNarrative {
  id        String   @id
  period    String                          // "2026-04"
  version   Int
  bodyMd    String
  citations Json
  confidence Float
  status    NarrativeStatus                  // draft | approved | sent
  createdAt DateTime
}
```

---

## 8. Formatting helpers

```ts
// formatINR.ts
export function inrCr(amount: number): string {
  return `₹${(amount / 1e7).toFixed(1)} Cr`;
}
export function inrShort(amount: number): string {       // "₹2,847" "₹0.94 Cr"
  if (amount >= 1e7) return inrCr(amount);
  if (amount >= 1e5) return `₹${(amount / 1e5).toFixed(2)} L`;
  return new Intl.NumberFormat('en-IN', { style:'currency', currency:'INR', maximumFractionDigits:0 }).format(amount);
}

// formatAge.ts
export function ageDays(opened: Date): string {
  const d = Math.floor((Date.now() - opened.getTime()) / 86_400_000);
  return `${d}d`;
}

// formatRelative.ts
export function relTime(iso: string): string {           // "just now" "2 min ago" "3 hr ago"
  const s = (Date.now() - new Date(iso).getTime()) / 1000;
  if (s < 30)   return 'just now';
  if (s < 3600) return `${Math.floor(s/60)} min ago`;
  if (s < 86400) return `${Math.floor(s/3600)} hr ago`;
  return `${Math.floor(s/86400)} d ago`;
}
```

---

## 9. Acceptance checklist

- [ ] At 1440×1120 the page renders 1:1 with no horizontal/vertical scroll.
- [ ] At smaller viewports the canvas scales proportionally; no layout reflow.
- [ ] All 6 KPI values count up on mount; clock in context bar ticks every second.
- [ ] Variance panel correctly scales bars to `maxRevenue` and totals match the row sum.
- [ ] Clicking a cluster row navigates to its drill page.
- [ ] Cluster tabs filter the list and update counts.
- [ ] SLA bucket totals + breach list reconcile with the same `/sla` payload.
- [ ] Insights stream receives SSE events and prepends them; oldest gets trimmed at 4.
- [ ] Chat composer streams tokens and shows tool-pills as tools fire.
- [ ] Citation chips open the cited entity in a side sheet.
- [ ] Narrative panel renders the latest `MonthlyNarrative` version; `Regenerate` triggers a new draft and re-streams; `Approve draft` flips status to `approved`.
- [ ] All copy and color tokens match `colors_and_type.css`.

---

## 10. Files in this bundle

| File | Purpose |
|------|---------|
| `Auditor Cockpit.html`            | The hi-fi design reference for the entire cockpit |
| `Revenue Assurance Solution.html` | The 9-slide context deck (use slide 2 for agent list, slide 5 for architecture, slide 8 for tech stack) |
| `colors_and_type.css`             | Uniqus design tokens (copy values into Tailwind config) |
| `slides.css`                      | Slide chrome — only referenced by the deck file, ignore for cockpit |
| `assets/logo-uniqus.png`          | Brand logo (use in top-bar; in mock it's an inline gradient tile) |

---

## 11. Out of scope (this handoff)

- Cluster drill page (`/cockpit/clusters/[id]`) — separate handoff
- Exception detail / approve-dispute flows — separate
- Mobile / tablet layouts
- Auth + role gating implementation details (assume project conventions)
- Real connectors to Finacle, Finone, VisionPlus, Murex — backend team's pipe
