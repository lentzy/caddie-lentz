# Golf Tracker App — Design Spec

**Date:** 2026-03-22
**Status:** Draft
**Project:** caddie-lentz

---

## Overview

A web app for tracking golf scores and statistics over time. The core purpose is not just recording data — it is surfacing the 1-2 areas of the game most holding the user back, so they can focus practice deliberately. Built for personal use with the ability to share with a small group of friends.

---

## Goals

- Track scores and statistics for every round
- Identify and display Focus Areas: the top 1-2 weaknesses based on recent play
- Support shot-level tracking for deeper pattern analysis
- Allow friends to use the app with their own private data
- Architect for future social/comparison features without building them now

---

## Non-Goals (V1)

- Social features / leaderboards / friend comparisons
- Handicap index tracking (data model supports it, not surfaced in UI)
- Scorecard photo scanning
- Strokes gained (Broadie methodology)
- Practice plan generator
- Dedicated putting analytics table

---

## Tech Stack

| Layer | Tool |
|-------|------|
| App framework | Streamlit (Python) |
| Database | Supabase (hosted Postgres) |
| Auth | Supabase Auth (email + password) |
| Charts | Plotly |
| Hosting | Streamlit Community Cloud (free tier) |
| Source control | GitHub |

### Mobile-First Design

The app is designed mobile-first. The primary use case — entering hole scores and shots — happens on a phone on the golf course. All UI decisions should assume a small screen first:

- Single-column layouts as the default; avoid side-by-side columns on data entry screens
- Large, easy-to-tap buttons and inputs (especially for hole entry)
- Minimal horizontal scrolling — no wide tables on entry screens
- Use cards/containers over data tables where possible on mobile-heavy pages
- `use_container_width=True` on all charts
- The hole entry screen is the most critical mobile flow — keep it simple and thumb-friendly
- Dashboard and Stats pages are secondary (viewed after the round) but should still render well on mobile

### Architecture Principles

The app is split into three layers to keep the Streamlit frontend replaceable:

1. **Data layer** (`db.py`) — all Supabase reads/writes. No database calls in UI code.
2. **Analytics layer** (`analytics.py`) — computes stats, trends, and focus area recommendations. Pure Python/pandas, no UI concerns.
3. **UI layer** — Streamlit pages. Kept thin. Calls data and analytics layers only.

---

## Data Model

### `users`
Managed entirely by Supabase Auth. Fields: id, email, password (hashed), created_at.
A `display_name` can be stored in a Supabase Auth user metadata field.

---

### `courses`
Shared across all users. Anyone can create; only the creator can edit/delete.

| Field | Type | Notes |
|-------|------|-------|
| id | uuid | PK |
| created_by_user_id | uuid | FK to users |
| name | text | |
| city | text | |
| state | text | |
| number_of_holes | integer | Always 18 in V1; field exists to support 9-hole courses in future |
| par_per_hole | integer[18] | Array indexed by hole number |
| created_at | timestamptz | |

---

### `tees`
Multiple tees per course. Shared across all users.

| Field | Type | Notes |
|-------|------|-------|
| id | uuid | PK |
| course_id | uuid | FK to courses |
| created_by_user_id | uuid | FK to users |
| tee_name | text | e.g. "Blue", "White", "Red" |
| rating | decimal | Course rating |
| slope | integer | Slope rating |
| yardage_per_hole | integer[18] | Array indexed by hole number |
| created_at | timestamptz | |

---

### `rounds`
One row per round played.

| Field | Type | Notes |
|-------|------|-------|
| id | uuid | PK |
| user_id | uuid | FK to users |
| course_id | uuid | FK to courses |
| tee_id | uuid | FK to tees |
| date | date | |
| holes_played | enum | full / front_9 / back_9 |
| status | enum | in_progress / complete |
| total_score | integer | Populated on completion |
| differential | decimal | (113/slope) * (score - rating) for 18-hole rounds; null for 9-hole rounds in V1 |
| notes | text | Optional |
| created_at | timestamptz | |

---

### `hole_scores`
One row per hole per round.

| Field | Type | Notes |
|-------|------|-------|
| id | uuid | PK |
| round_id | uuid | FK to rounds |
| hole_number | integer | 1–18 |
| score | integer | Strokes for the hole |
| putts | integer | Total putts (authoritative — not tracked in shots) |
| fairway_hit | enum | yes / no / na (par 3s = na) |
| green_in_regulation | boolean | Manually entered — user's judgment, since the ball may have reached the green in regulation but rolled off |
| penalties | integer | Total penalty strokes for the hole |
| created_at | timestamptz | |

---

### `shots`
One row per shot tracked. Optional — rounds and holes can be logged without any shot data.
Putts are excluded from shot tracking; they are captured on `hole_scores`.

| Field | Type | Notes |
|-------|------|-------|
| id | uuid | PK |
| hole_score_id | uuid | FK to hole_scores |
| shot_number | integer | Sequence within the hole |
| distance_to_hole | integer | Yards, from rangefinder |
| club | text | Selected from predefined list (see Club List below) |
| shot_type | enum | tee / fairway / rough / sand / other |
| lie | enum | good / bad |
| contact | text[] | Multi-select array — a shot can have multiple contact types (e.g. fat + toe). Values: good / chunk / top / fat / thin / toe / heel / other |
| miss_direction | enum | left / right — nullable |
| outcome | enum | fairway / green / penalty / other |
| penalty_reason | enum | ob / water / unplayable / lost_ball / other — nullable |
| distance_hit | integer | Optional, yards |
| created_at | timestamptz | |

---

### Club List (Predefined)

The full club list available to all users:

| Category | Clubs |
|----------|-------|
| Woods | Driver, 3W, 5W, 7W |
| Hybrids | 2H, 3H, 4H, 5H |
| Irons | 2i, 3i, 4i, 5i, 6i, 7i, 8i, 9i |
| Wedges | PW, GW, SW, LW, 48°, 50°, 52°, 54°, 56°, 58°, 60°, 62°, 64° |
| Putter | Putter |

Users configure **their bag** in Profile/Settings — a saved subset of this list representing the clubs they actually carry. The shot entry screen shows their bag clubs by default, with the full list available as a fallback. Bag configuration is stored in the `user_bag` table.

### `user_bag`
One row per club per user.

| Field | Type | Notes |
|-------|------|-------|
| id | uuid | PK |
| user_id | uuid | FK to users |
| club | text | Must be a value from the predefined club list |
| created_at | timestamptz | |

---

## Row-Level Security (RLS)

| Table | Read | Write/Update/Delete |
|-------|------|---------------------|
| courses | All authenticated users | Creator only |
| tees | All authenticated users | Creator only |
| rounds | Owner only | Owner only |
| hole_scores | Owner (via round) | Owner (via round) |
| shots | Owner (via hole_score) | Owner (via hole_score) |
| user_bag | Owner only | Owner only |

**Note:** Courses are immutable once any round references them (enforce at app layer in v1, consider DB constraint in v2).

---

## Pages & Navigation

Streamlit sidebar navigation. Displays user display name and logout button at top.

### 1. Auth Pages
- Login (email + password)
- Register
- Forgot Password
- Handled mostly by Supabase Auth; minimal custom UI needed.

### 2. Dashboard (Home)
The first thing a user sees. Ordered by priority:

1. **Focus Areas card** (prominent, top of page) — top 1-2 weaknesses with plain-English explanation and shot-pattern sub-bullet
2. **In-Progress Round banner** — "Continue Round" button if a round has `status = in_progress`
3. Scoring trend chart (last 20 rounds)
4. Key stat trends: putts/round, GIR %, fairways hit % (last 20 rounds)

### 3. New Round
Step-by-step flow:
1. Select course (search/browse shared course library) or add a new course
2. Select tee
3. Select holes played (Full 18 / Front 9 / Back 9)
4. Hole-by-hole entry (default flow)
5. Review & Submit

**Hole entry screen** (per hole):
- Shows: hole number, par, yardage from selected tee
- Fields: score, putts, fairway hit, GIR, penalties
- Expandable "Track Shots" section for optional shot-level logging
- Previous / Next hole navigation
- Progress indicator (e.g. "Hole 4 of 18")
- Each hole saved immediately on Next — data is not lost if app closes

### 4. Round History
- List of all completed rounds: date, course, score, holes played
- Click into a round for full hole-by-hole breakdown and shot log
- Edit a completed round: user can update any hole's score, putts, fairway hit, GIR, penalties, or shot data. Saving recalculates `total_score` and `differential` on the round.

### 5. Course Manager
- Browse all courses (shared library) — sorted alphabetically, simple text search filter, no pagination in V1
- Add a new course (name, city, state, par per hole)
- Add tees to a course (name, rating, slope, yardages per hole)
- Edit/delete only for courses/tees you created

### 6. Stats & Analysis
- Deeper dive charts: score distribution, per-hole averages, stat trends over time
- Shot analysis: outcome breakdown by club, distance, shot_type, lie
- "Where am I losing strokes?" view comparing your metrics to interpolated benchmarks

### 7. Profile / Settings
- Update display name
- Change password
- **My Bag** — select which clubs from the predefined list you carry. Saved to `user_bag`. Shot entry screens show these clubs by default.

---

## Analytics & Focus Areas Logic

All computed in `analytics.py` using pandas. No AI or external service required.

### Step 1 — Compute metrics per round
- Putts/round
- Putts per GIR (pure putting quality)
- GIR %
- Fairways hit %
- Scoring average by par type (par 3 / 4 / 5)
- Penalty rate (penalties per round)
- Shot outcome/contact breakdown by club, distance bucket, shot_type, lie

### Step 2 — Compare against benchmarks
Each metric is compared against three reference points, all displayed in the Stats & Analysis page and used in Focus Area gap calculations:

1. **Your last 20 rounds** — your own recent average
2. **Bogey golfer (~95)** — a fixed baseline for a typical recreational golfer
3. **Scratch golfer (72)** — a fixed aspirational baseline

| Metric | Scratch (72) | Bogey (~95) |
|--------|-------------|-------------|
| Putts/round | 29 | 36 |
| GIR % | 67% | 25% |
| Fairways hit % | 62% | 40% |
| Penalties/round | 0.5 | 3 |
| Scoring avg par 3 | 3.1 | 4.0 |
| Scoring avg par 4 | 4.2 | 5.5 |
| Scoring avg par 5 | 5.0 | 6.5 |

For Focus Area gap ranking, the interpolated personal target (linear interpolation between scratch and bogey anchors based on the user's average score) is used as the comparison point — not scratch. This ensures the gap reflects realistic improvement opportunity. For scores outside the range (below 72 or above 95), clamp to the nearest anchor.

### Step 3 — Rank gaps with trend weighting
For each metric:
- Compute absolute gap vs interpolated benchmark (70% weight)
- Compute trend: recent 5 rounds vs prior 5 rounds (30% weight)
- A declining metric is weighted higher even if absolute gap is smaller

Surface the top 2 metrics as Focus Areas.

### Step 4 — Generate Focus Area sub-bullets
Requires minimum 3 rounds with shot tracking data within the last 20 rounds. Below this threshold, show headline metric only.

Sub-bullets use shot data available in V1 (`shots` table). The putting example below is noted as a future enhancement only — putt distance is not tracked in V1.

Examples:
> **Approach Play (GIR 18%)**
> 60% of missed greens are misses right — likely a consistent ball flight issue

> **Putting (38 putts/round)**
> High 3-putt rate — consider tracking individual putts for deeper analysis (future feature)

> **Driving (Fairways 30%)**
> 65% of missed fairways are left — suggests a pull or hook pattern

---

## Validation Rules

- `score` per hole: 1–15 (warn if > 10, do not block)
- `putts` per hole: 0–6; must not exceed `score`
- `penalties` per hole: 0–`score`
- `total_score`: computed as sum of all `hole_scores.score` for the round
- `total_score` for 9-hole rounds: sum of 9 holes played (not adjusted to 18-hole equivalent)
- Shot `distance_to_hole`: 0–600 yards
- Shot `distance_hit`: 0–400 yards

---

## Round Entry — Implementation Notes

> These are implementation guidance notes, not testable requirements.

Streamlit reruns the entire script on every interaction. The hole-by-hole flow requires careful state management:

- Use `st.form` for each hole's data entry to batch submissions and prevent double-writes
- Use `st.session_state` for current hole number, in-progress hole data, and round context
- Every hole submission is a complete, independent database write
- On app restart/reauth, reload round state from the database, not from session state
- Auth tokens must be refreshed proactively — a user may leave the app open for a full round (4+ hours)

---

## Database Migrations

Use numbered SQL migration files tracked in the repo:
```
db/migrations/
  001_initial_schema.sql
  002_add_status_to_rounds.sql
  ...
```

Use Supabase CLI (`supabase migration new`, `supabase db push`) from day one. Never edit the schema directly in the Supabase dashboard without a corresponding migration file.

---

## Future Roadmap (Out of Scope for V1)

| Feature | Notes |
|---------|-------|
| Social / leaderboard | Data model (user_id on all rows) already supports this |
| Handicap index tracking | `differential` already stored on rounds |
| Scorecard photo scanning | AI vision (Claude or GPT-4 Vision) parses image into round entry form |
| Strokes gained | Broadie lookup tables; see "Every Shot Counts" for methodology |
| Practice plan generator | Hardcoded drill library or LLM-generated based on Focus Areas |
| Putting analytics | Dedicated `putts` table with distance, break, outcome per putt |
| Google OAuth | Can be added via Supabase Auth settings with minimal code changes |

---

## Open Questions / Known Limitations

- **Course editing:** If a course's par is corrected after rounds have been logged against it, historical stats may shift. Mitigate in v1 by restricting edits to the creator and flagging the risk in the UI.
- **9-hole second loop:** Playing the same 9 holes twice in one round is not supported in v1. Known limitation.
- **Shot tracking for putts:** Putts are tracked as a count on `hole_scores` only. A dedicated `putts` table with per-putt distance, break, and outcome is noted for a future version.
- **Club list extensibility:** The predefined club list is hardcoded in V1. Custom clubs (e.g. off-brand wedges, unusual hybrids) are not supported. Consider user-defined custom clubs in a future version.
