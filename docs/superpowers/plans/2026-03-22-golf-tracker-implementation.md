# Golf Tracker (caddie-lentz) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Streamlit + Supabase golf tracking web app that records rounds hole-by-hole, tracks shot data, and surfaces the top 1-2 practice focus areas based on recent performance.

**Architecture:** Three-layer Python app — `db.py` owns all Supabase I/O, `analytics.py` owns all stats computation, Streamlit pages stay thin and call those two layers only. This keeps the frontend replaceable without touching business logic.

**Tech Stack:** Python 3.11+, Streamlit, supabase-py v2, pandas, Plotly, pytest, Supabase (hosted Postgres + Auth), Streamlit Community Cloud.

**Mobile-First:** All UI is designed for small screens first. The primary use case (entering hole scores on the course) happens on a phone. Rules for every page:
- Single-column layouts on all data entry screens — no side-by-side columns on hole entry
- Large buttons and inputs — easy to tap with a thumb
- No horizontal scrolling — avoid wide multi-column tables
- `use_container_width=True` on every chart
- Prefer cards/metric widgets over tables for summary data
- Minimize text — labels should be short and scannable on a small screen

---

## File Map

| File | Responsibility |
|------|---------------|
| `app.py` | Entry point, auth gate, sidebar navigation |
| `src/constants.py` | Club list, benchmark values, all enums |
| `src/auth.py` | Supabase client init, login/register/logout, token refresh |
| `src/db.py` | All CRUD functions against Supabase |
| `src/analytics.py` | Metrics computation, benchmark interpolation, focus area ranking |
| `pages/1_Dashboard.py` | Focus Areas card, scoring trends, continue-round banner |
| `pages/2_New_Round.py` | Course selection → hole-by-hole entry → shot tracking → submit |
| `pages/3_Round_History.py` | Round list, detail view, edit flow |
| `pages/4_Course_Manager.py` | Browse/add/edit courses and tees |
| `pages/5_Stats.py` | Deep stat charts, benchmark comparison table |
| `pages/6_Profile.py` | Display name, password, My Bag configuration |
| `db/migrations/001_initial_schema.sql` | Full DB schema + RLS policies |
| `tests/test_constants.py` | Validate club list and benchmark tables |
| `tests/test_analytics.py` | Unit tests for all analytics functions |
| `tests/test_db.py` | Unit tests for db functions (mocked Supabase client) |

---

## Task 1: Project Scaffold

**Files:**
- Create: `requirements.txt`
- Create: `.streamlit/secrets.toml.example`
- Create: `.streamlit/config.toml`
- Create: `app.py`
- Create: `src/__init__.py`
- Create: `pages/.gitkeep`
- Create: `tests/__init__.py`
- Create: `db/migrations/.gitkeep`
- Create: `README.md`

- [ ] **Step 1: Create the project directory structure**

```bash
cd /c/Users/lentz/projects/lentz-caddie
mkdir -p src pages db/migrations tests .streamlit
touch src/__init__.py tests/__init__.py
```

- [ ] **Step 2: Write requirements.txt**

```
streamlit>=1.32.0
supabase>=2.4.0
pandas>=2.0.0
plotly>=5.18.0
pytest>=7.4.0
pytest-mock>=3.12.0
python-dotenv>=1.0.0
```

- [ ] **Step 3: Create .streamlit/secrets.toml.example**

```toml
# Copy this to .streamlit/secrets.toml and fill in your values.
# Never commit secrets.toml to git.
SUPABASE_URL = "https://your-project-id.supabase.co"
SUPABASE_ANON_KEY = "your-anon-key-here"
```

- [ ] **Step 4: Create .streamlit/config.toml**

```toml
[theme]
base = "light"

[server]
headless = true
```

- [ ] **Step 5: Create a minimal app.py**

```python
import streamlit as st

st.set_page_config(
    page_title="Lentz Caddie",
    page_icon="⛳",
    layout="wide",
)

st.title("Lentz Caddie")
st.write("Golf score and statistics tracker.")
```

- [ ] **Step 6: Add .gitignore**

```
.streamlit/secrets.toml
__pycache__/
*.pyc
.env
.venv/
venv/
*.egg-info/
.pytest_cache/
```

- [ ] **Step 7: Initialize git and make first commit**

```bash
cd /c/Users/lentz/projects/lentz-caddie
git init
git add .
git commit -m "feat: initial project scaffold"
```

- [ ] **Step 8: Initialize Supabase CLI for migration tracking**

Install the Supabase CLI (one-time):
```bash
# On Windows via npm:
npm install -g supabase
# Or via Scoop: scoop install supabase
```

Initialize in the project:
```bash
supabase init
```

This creates a `supabase/` config directory. For V1, we apply the migration manually via the Supabase dashboard SQL editor (see Task 2), but the CLI is used for future migrations with `supabase migration new` and `supabase db push`.

- [ ] **Step 9: Install dependencies and verify Streamlit runs**

```bash
pip install -r requirements.txt
streamlit run app.py
```

Expected: Streamlit opens in browser showing "Lentz Caddie".

---

## Task 2: Database Schema & Migrations

**Files:**
- Create: `db/migrations/001_initial_schema.sql`

**Prerequisites:** You need a Supabase account and project.
1. Go to supabase.com → New Project
2. Save your project URL and anon key to `.streamlit/secrets.toml`
3. Install Supabase CLI: `npm install -g supabase` (or via homebrew)

- [ ] **Step 1: Write the migration file**

```sql
-- db/migrations/001_initial_schema.sql

-- courses: shared library, anyone can create, only creator can edit
CREATE TABLE courses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_by_user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    city TEXT NOT NULL,
    state TEXT NOT NULL,
    number_of_holes INTEGER NOT NULL DEFAULT 18,
    par_per_hole INTEGER[] NOT NULL,  -- length 18
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- tees: multiple per course
CREATE TABLE tees (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    created_by_user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    tee_name TEXT NOT NULL,
    rating NUMERIC(4,1) NOT NULL,
    slope INTEGER NOT NULL,
    yardage_per_hole INTEGER[] NOT NULL,  -- length 18
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- rounds: one per round played
CREATE TYPE round_holes_played AS ENUM ('full', 'front_9', 'back_9');
CREATE TYPE round_status AS ENUM ('in_progress', 'complete');

CREATE TABLE rounds (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    course_id UUID NOT NULL REFERENCES courses(id),
    tee_id UUID NOT NULL REFERENCES tees(id),
    date DATE NOT NULL,
    holes_played round_holes_played NOT NULL DEFAULT 'full',
    status round_status NOT NULL DEFAULT 'in_progress',
    total_score INTEGER,
    differential NUMERIC(5,2),
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- hole_scores: one per hole per round
CREATE TYPE fairway_hit_type AS ENUM ('yes', 'no', 'na');

CREATE TABLE hole_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    round_id UUID NOT NULL REFERENCES rounds(id) ON DELETE CASCADE,
    hole_number INTEGER NOT NULL CHECK (hole_number BETWEEN 1 AND 18),
    score INTEGER NOT NULL CHECK (score BETWEEN 1 AND 15),
    putts INTEGER NOT NULL CHECK (putts BETWEEN 0 AND 6),
    fairway_hit fairway_hit_type NOT NULL DEFAULT 'na',
    green_in_regulation BOOLEAN NOT NULL DEFAULT false,
    penalties INTEGER NOT NULL DEFAULT 0 CHECK (penalties >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (round_id, hole_number)
);

-- shots: optional, one per shot tracked (putts excluded)
CREATE TYPE shot_type_enum AS ENUM ('tee', 'fairway', 'rough', 'sand', 'other');
CREATE TYPE lie_enum AS ENUM ('good', 'bad');
CREATE TYPE miss_direction_enum AS ENUM ('left', 'right');
CREATE TYPE outcome_enum AS ENUM ('fairway', 'green', 'penalty', 'other');
CREATE TYPE penalty_reason_enum AS ENUM ('ob', 'water', 'unplayable', 'lost_ball', 'other');

CREATE TABLE shots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hole_score_id UUID NOT NULL REFERENCES hole_scores(id) ON DELETE CASCADE,
    shot_number INTEGER NOT NULL,
    distance_to_hole INTEGER CHECK (distance_to_hole BETWEEN 0 AND 600),
    club TEXT NOT NULL,
    shot_type shot_type_enum NOT NULL,
    lie lie_enum NOT NULL,
    contact TEXT[] NOT NULL DEFAULT '{}',
    miss_direction miss_direction_enum,
    outcome outcome_enum NOT NULL,
    penalty_reason penalty_reason_enum,
    distance_hit INTEGER CHECK (distance_hit BETWEEN 0 AND 400),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- user_bag: per-user club selection
CREATE TABLE user_bag (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    club TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, club)
);

-- ============================================================
-- Row Level Security
-- ============================================================

ALTER TABLE courses ENABLE ROW LEVEL SECURITY;
ALTER TABLE tees ENABLE ROW LEVEL SECURITY;
ALTER TABLE rounds ENABLE ROW LEVEL SECURITY;
ALTER TABLE hole_scores ENABLE ROW LEVEL SECURITY;
ALTER TABLE shots ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_bag ENABLE ROW LEVEL SECURITY;

-- courses: all authenticated users can read; only creator can write
CREATE POLICY "courses_read" ON courses FOR SELECT TO authenticated USING (true);
CREATE POLICY "courses_insert" ON courses FOR INSERT TO authenticated WITH CHECK (created_by_user_id = auth.uid());
CREATE POLICY "courses_update" ON courses FOR UPDATE TO authenticated USING (created_by_user_id = auth.uid());
CREATE POLICY "courses_delete" ON courses FOR DELETE TO authenticated USING (created_by_user_id = auth.uid());

-- tees: same as courses
CREATE POLICY "tees_read" ON tees FOR SELECT TO authenticated USING (true);
CREATE POLICY "tees_insert" ON tees FOR INSERT TO authenticated WITH CHECK (created_by_user_id = auth.uid());
CREATE POLICY "tees_update" ON tees FOR UPDATE TO authenticated USING (created_by_user_id = auth.uid());
CREATE POLICY "tees_delete" ON tees FOR DELETE TO authenticated USING (created_by_user_id = auth.uid());

-- rounds: owner only
CREATE POLICY "rounds_owner" ON rounds FOR ALL TO authenticated USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());

-- hole_scores: owner via round
CREATE POLICY "hole_scores_owner" ON hole_scores FOR ALL TO authenticated
    USING (EXISTS (SELECT 1 FROM rounds WHERE rounds.id = hole_scores.round_id AND rounds.user_id = auth.uid()))
    WITH CHECK (EXISTS (SELECT 1 FROM rounds WHERE rounds.id = hole_scores.round_id AND rounds.user_id = auth.uid()));

-- shots: owner via hole_score
CREATE POLICY "shots_owner" ON shots FOR ALL TO authenticated
    USING (EXISTS (
        SELECT 1 FROM hole_scores
        JOIN rounds ON rounds.id = hole_scores.round_id
        WHERE hole_scores.id = shots.hole_score_id AND rounds.user_id = auth.uid()
    ))
    WITH CHECK (EXISTS (
        SELECT 1 FROM hole_scores
        JOIN rounds ON rounds.id = hole_scores.round_id
        WHERE hole_scores.id = shots.hole_score_id AND rounds.user_id = auth.uid()
    ));

-- user_bag: owner only
CREATE POLICY "user_bag_owner" ON user_bag FOR ALL TO authenticated USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());
```

- [ ] **Step 2: Apply migration via Supabase dashboard**

In V1, apply this manually:
1. Go to your Supabase project → SQL Editor
2. Paste the contents of `001_initial_schema.sql`
3. Click Run

Expected: All tables created, no errors.

> For future schema changes, use `supabase migration new <name>` to create a new numbered SQL file, then `supabase db push` to apply it. Never edit the schema directly in the dashboard without a matching migration file.

- [ ] **Step 3: Verify tables exist in Supabase**

In Supabase → Table Editor, confirm these tables appear: `courses`, `tees`, `rounds`, `hole_scores`, `shots`, `user_bag`.

- [ ] **Step 4: Commit**

```bash
git add db/
git commit -m "feat: add initial database schema and RLS policies"
```

---

## Task 3: Constants

**Files:**
- Create: `src/constants.py`
- Create: `tests/test_constants.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_constants.py
from src.constants import CLUB_LIST, BENCHMARKS, CONTACT_OPTIONS, OUTCOME_OPTIONS

def test_club_list_has_all_categories():
    clubs = [c for cats in CLUB_LIST.values() for c in cats]
    assert "Driver" in clubs
    assert "7i" in clubs
    assert "SW" in clubs
    assert "58°" in clubs
    assert "Putter" in clubs

def test_club_list_no_duplicates():
    clubs = [c for cats in CLUB_LIST.values() for c in cats]
    assert len(clubs) == len(set(clubs))

def test_benchmarks_have_all_metrics():
    for level in ("scratch", "bogey"):
        assert "putts_per_round" in BENCHMARKS[level]
        assert "gir_pct" in BENCHMARKS[level]
        assert "fairways_hit_pct" in BENCHMARKS[level]
        assert "penalties_per_round" in BENCHMARKS[level]
        assert "scoring_avg_par3" in BENCHMARKS[level]
        assert "scoring_avg_par4" in BENCHMARKS[level]
        assert "scoring_avg_par5" in BENCHMARKS[level]

def test_scratch_better_than_bogey():
    assert BENCHMARKS["scratch"]["putts_per_round"] < BENCHMARKS["bogey"]["putts_per_round"]
    assert BENCHMARKS["scratch"]["gir_pct"] > BENCHMARKS["bogey"]["gir_pct"]

def test_contact_options_are_list_of_strings():
    assert isinstance(CONTACT_OPTIONS, list)
    assert "good" in CONTACT_OPTIONS
    assert "chunk" in CONTACT_OPTIONS
    assert "toe" in CONTACT_OPTIONS
    assert "heel" in CONTACT_OPTIONS
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_constants.py -v
```

Expected: ImportError — `src.constants` does not exist.

- [ ] **Step 3: Write src/constants.py**

```python
# src/constants.py

CLUB_LIST = {
    "Woods": ["Driver", "3W", "5W", "7W"],
    "Hybrids": ["2H", "3H", "4H", "5H"],
    "Irons": ["2i", "3i", "4i", "5i", "6i", "7i", "8i", "9i"],
    "Wedges": ["PW", "GW", "SW", "LW", "48°", "50°", "52°", "54°", "56°", "58°", "60°", "62°", "64°"],
    "Putter": ["Putter"],
}

ALL_CLUBS = [club for clubs in CLUB_LIST.values() for club in clubs]

# Benchmark values for scratch (avg score ~72) and bogey (~95) golfers
BENCHMARKS = {
    "scratch": {
        "avg_score": 72,
        "putts_per_round": 29,
        "gir_pct": 0.67,
        "fairways_hit_pct": 0.62,
        "penalties_per_round": 0.5,
        "scoring_avg_par3": 3.1,
        "scoring_avg_par4": 4.2,
        "scoring_avg_par5": 5.0,
    },
    "bogey": {
        "avg_score": 95,
        "putts_per_round": 36,
        "gir_pct": 0.25,
        "fairways_hit_pct": 0.40,
        "penalties_per_round": 3.0,
        "scoring_avg_par3": 4.0,
        "scoring_avg_par4": 5.5,
        "scoring_avg_par5": 6.5,
    },
}

SHOT_TYPE_OPTIONS = ["tee", "fairway", "rough", "sand", "other"]
LIE_OPTIONS = ["good", "bad"]
CONTACT_OPTIONS = ["good", "chunk", "top", "fat", "thin", "toe", "heel", "other"]
MISS_DIRECTION_OPTIONS = ["left", "right"]
OUTCOME_OPTIONS = ["fairway", "green", "penalty", "other"]
PENALTY_REASON_OPTIONS = ["ob", "water", "unplayable", "lost_ball", "other"]

HOLES_PLAYED_OPTIONS = {
    "Full 18": "full",
    "Front 9 (holes 1-9)": "front_9",
    "Back 9 (holes 10-18)": "back_9",
}

HOLES_FOR_ROUND = {
    "full": list(range(1, 19)),
    "front_9": list(range(1, 10)),
    "back_9": list(range(10, 19)),
}

FAIRWAY_HIT_OPTIONS = ["yes", "no", "na"]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_constants.py -v
```

Expected: All 5 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/constants.py tests/test_constants.py
git commit -m "feat: add constants for clubs, benchmarks, and enums"
```

---

## Task 4: Auth Module

> **Forgot Password:** Supabase handles the full email reset flow. The app only needs to call `client.auth.reset_password_for_email(email)` and show a confirmation message. Add a "Forgot password?" link on the login tab that triggers this call.

**Files:**
- Create: `src/auth.py`

- [ ] **Step 1: Write src/auth.py**

```python
# src/auth.py
import streamlit as st
from supabase import create_client, Client


def get_supabase_client() -> Client:
    """Initialize or return the Supabase client from session state."""
    if "supabase" not in st.session_state:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_ANON_KEY"]
        st.session_state.supabase = create_client(url, key)
    return st.session_state.supabase


def refresh_session_if_needed():
    """Refresh the auth token if it is close to expiring."""
    client = get_supabase_client()
    try:
        session = client.auth.get_session()
        if session is None:
            st.session_state.pop("user", None)
    except Exception:
        st.session_state.pop("user", None)


def is_authenticated() -> bool:
    return "user" in st.session_state and st.session_state.user is not None


def require_auth():
    """Call at top of every page. Redirects to login if not authenticated."""
    refresh_session_if_needed()
    if not is_authenticated():
        st.warning("Please log in to continue.")
        st.stop()


def login(email: str, password: str) -> tuple[bool, str]:
    """Returns (success, error_message)."""
    client = get_supabase_client()
    try:
        response = client.auth.sign_in_with_password({"email": email, "password": password})
        st.session_state.user = response.user
        return True, ""
    except Exception as e:
        return False, str(e)


def register(email: str, password: str) -> tuple[bool, str]:
    """Returns (success, error_message)."""
    client = get_supabase_client()
    try:
        response = client.auth.sign_up({"email": email, "password": password})
        if response.user:
            st.session_state.user = response.user
            return True, ""
        return False, "Registration failed. Check your email for a confirmation link."
    except Exception as e:
        return False, str(e)


def logout():
    client = get_supabase_client()
    try:
        client.auth.sign_out()
    except Exception:
        pass
    st.session_state.pop("user", None)


def get_current_user():
    return st.session_state.get("user")


def get_current_user_id() -> str | None:
    user = get_current_user()
    return str(user.id) if user else None
```

- [ ] **Step 2: Update app.py to be the auth gate**

```python
# app.py
import streamlit as st
from src.auth import is_authenticated, login, register, logout, get_supabase_client

st.set_page_config(
    page_title="Lentz Caddie",
    page_icon="⛳",
    layout="wide",
)

# Initialize Supabase client on first load
get_supabase_client()

if is_authenticated():
    # Sidebar shown on all pages when authenticated
    with st.sidebar:
        user = st.session_state.user
        st.write(f"Logged in as **{user.email}**")
        if st.button("Logout"):
            logout()
            st.rerun()
    st.switch_page("pages/1_Dashboard.py")
else:
    st.title("⛳ Lentz Caddie")
    tab_login, tab_register = st.tabs(["Log In", "Register"])

    with tab_login:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Log In")
            if submitted:
                success, error = login(email, password)
                if success:
                    st.rerun()
                else:
                    st.error(f"Login failed: {error}")

    with tab_register:
        with st.form("register_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            password2 = st.text_input("Confirm Password", type="password")
            submitted = st.form_submit_button("Register")
            if submitted:
                if password != password2:
                    st.error("Passwords do not match.")
                elif len(password) < 6:
                    st.error("Password must be at least 6 characters.")
                else:
                    success, error = register(email, password)
                    if success:
                        st.success("Account created! Check your email to confirm, then log in.")
                    else:
                        st.error(f"Registration failed: {error}")
```

- [ ] **Step 3: Manually test login and registration**

```bash
streamlit run app.py
```

1. Click Register tab, create an account with a real email
2. Confirm email if required by Supabase settings
3. Log in — should redirect to Dashboard (blank for now)
4. Logout button should return to login screen

- [ ] **Step 4: Commit**

```bash
git add src/auth.py app.py
git commit -m "feat: add auth module with login, register, logout, and session management"
```

---

## Task 5: Data Layer — Courses & Tees

**Files:**
- Create: `src/db.py` (courses and tees sections)
- Create: `tests/test_db.py` (courses and tees tests)

- [ ] **Step 1: Write failing tests for course functions**

```python
# tests/test_db.py
from unittest.mock import MagicMock, patch
import pytest
from src.db import get_courses, create_course, get_tees, create_tee


def make_mock_client():
    """Return a mock Supabase client."""
    return MagicMock()


def test_get_courses_returns_list(mocker):
    client = make_mock_client()
    client.table.return_value.select.return_value.order.return_value.execute.return_value.data = [
        {"id": "abc", "name": "Augusta National", "city": "Augusta", "state": "GA"}
    ]
    result = get_courses(client)
    assert len(result) == 1
    assert result[0]["name"] == "Augusta National"


def test_get_courses_filters_by_search(mocker):
    client = make_mock_client()
    mock_chain = MagicMock()
    client.table.return_value.select.return_value.ilike.return_value.order.return_value.execute.return_value.data = [
        {"id": "abc", "name": "Augusta National"}
    ]
    result = get_courses(client, search="Augusta")
    assert len(result) == 1


def test_create_course_calls_insert(mocker):
    client = make_mock_client()
    client.table.return_value.insert.return_value.execute.return_value.data = [
        {"id": "new-id", "name": "Pebble Beach"}
    ]
    result = create_course(
        client,
        user_id="user-1",
        name="Pebble Beach",
        city="Pebble Beach",
        state="CA",
        par_per_hole=[4,5,4,4,3,5,3,4,4,4,4,3,4,5,4,4,3,5],
    )
    assert result["name"] == "Pebble Beach"
    client.table.return_value.insert.assert_called_once()


def test_create_course_rejects_wrong_par_length():
    client = make_mock_client()
    with pytest.raises(ValueError, match="par_per_hole must have exactly 18 values"):
        create_course(client, "u1", "Short Course", "City", "ST", [4, 4, 4])


def test_get_tees_for_course(mocker):
    client = make_mock_client()
    client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = [
        {"id": "t1", "tee_name": "Blue", "rating": 74.2, "slope": 138}
    ]
    result = get_tees(client, course_id="course-1")
    assert len(result) == 1
    assert result[0]["tee_name"] == "Blue"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_db.py -v
```

Expected: ImportError — `src.db` does not exist.

- [ ] **Step 3: Write src/db.py — courses and tees**

```python
# src/db.py
from supabase import Client


# ─────────────────────────────────────────────
# COURSES
# ─────────────────────────────────────────────

def get_courses(client: Client, search: str = None) -> list[dict]:
    """Return all courses, optionally filtered by name."""
    query = client.table("courses").select("*")
    if search:
        query = query.ilike("name", f"%{search}%")
    return query.order("name").execute().data


def get_course(client: Client, course_id: str) -> dict | None:
    result = client.table("courses").select("*").eq("id", course_id).execute()
    return result.data[0] if result.data else None


def create_course(
    client: Client,
    user_id: str,
    name: str,
    city: str,
    state: str,
    par_per_hole: list[int],
) -> dict:
    if len(par_per_hole) != 18:
        raise ValueError("par_per_hole must have exactly 18 values")
    result = client.table("courses").insert({
        "created_by_user_id": user_id,
        "name": name,
        "city": city,
        "state": state,
        "number_of_holes": 18,
        "par_per_hole": par_per_hole,
    }).execute()
    return result.data[0]


def update_course(client: Client, course_id: str, **kwargs) -> dict:
    result = client.table("courses").update(kwargs).eq("id", course_id).execute()
    return result.data[0]


def delete_course(client: Client, course_id: str):
    client.table("courses").delete().eq("id", course_id).execute()


# ─────────────────────────────────────────────
# TEES
# ─────────────────────────────────────────────

def get_tees(client: Client, course_id: str) -> list[dict]:
    return client.table("tees").select("*").eq("course_id", course_id).order("tee_name").execute().data


def get_tee(client: Client, tee_id: str) -> dict | None:
    result = client.table("tees").select("*").eq("id", tee_id).execute()
    return result.data[0] if result.data else None


def create_tee(
    client: Client,
    user_id: str,
    course_id: str,
    tee_name: str,
    rating: float,
    slope: int,
    yardage_per_hole: list[int],
) -> dict:
    if len(yardage_per_hole) != 18:
        raise ValueError("yardage_per_hole must have exactly 18 values")
    result = client.table("tees").insert({
        "created_by_user_id": user_id,
        "course_id": course_id,
        "tee_name": tee_name,
        "rating": rating,
        "slope": slope,
        "yardage_per_hole": yardage_per_hole,
    }).execute()
    return result.data[0]


def update_tee(client: Client, tee_id: str, **kwargs) -> dict:
    result = client.table("tees").update(kwargs).eq("id", tee_id).execute()
    return result.data[0]


def delete_tee(client: Client, tee_id: str):
    client.table("tees").delete().eq("id", tee_id).execute()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_db.py -v
```

Expected: All 5 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/db.py tests/test_db.py
git commit -m "feat: add data layer for courses and tees"
```

---

## Task 6: Data Layer — Rounds & Hole Scores

**Files:**
- Modify: `src/db.py` (add rounds and hole_scores functions)
- Modify: `tests/test_db.py` (add rounds and hole_scores tests)

- [ ] **Step 1: Add failing tests**

```python
# Add to tests/test_db.py
from src.db import (
    create_round, get_round, get_rounds, get_in_progress_round,
    complete_round, upsert_hole_score, get_hole_scores
)

def test_create_round(mocker):
    client = make_mock_client()
    client.table.return_value.insert.return_value.execute.return_value.data = [
        {"id": "r1", "status": "in_progress", "user_id": "u1"}
    ]
    result = create_round(client, user_id="u1", course_id="c1", tee_id="t1",
                          date="2026-03-22", holes_played="full")
    assert result["status"] == "in_progress"


def test_get_in_progress_round_returns_none_when_absent(mocker):
    client = make_mock_client()
    client.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
    result = get_in_progress_round(client, user_id="u1")
    assert result is None


def test_complete_round_sets_total_score(mocker):
    client = make_mock_client()
    # get_hole_scores returns 18 holes
    hole_scores = [{"score": 5, "round_id": "r1"} for _ in range(18)]
    client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = hole_scores
    # get_round returns tee info
    client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"id": "r1", "tee_id": "t1", "holes_played": "full",
         "tees": {"rating": 72.0, "slope": 113}}
    ]
    client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
        {"id": "r1", "total_score": 90, "status": "complete"}
    ]
    result = complete_round(client, round_id="r1")
    client.table.return_value.update.assert_called()


def test_upsert_hole_score(mocker):
    client = make_mock_client()
    client.table.return_value.upsert.return_value.execute.return_value.data = [
        {"id": "hs1", "hole_number": 1, "score": 4}
    ]
    result = upsert_hole_score(client, round_id="r1", hole_number=1,
                               score=4, putts=2, fairway_hit="yes",
                               green_in_regulation=True, penalties=0)
    assert result["hole_number"] == 1
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/test_db.py::test_create_round tests/test_db.py::test_complete_round_sets_total_score -v
```

Expected: ImportError for new functions.

- [ ] **Step 3: Add rounds and hole_scores to src/db.py**

```python
# Add to src/db.py

# ─────────────────────────────────────────────
# ROUNDS
# ─────────────────────────────────────────────

def create_round(
    client: Client,
    user_id: str,
    course_id: str,
    tee_id: str,
    date: str,
    holes_played: str = "full",
    notes: str = None,
) -> dict:
    result = client.table("rounds").insert({
        "user_id": user_id,
        "course_id": course_id,
        "tee_id": tee_id,
        "date": date,
        "holes_played": holes_played,
        "status": "in_progress",
        "notes": notes,
    }).execute()
    return result.data[0]


def get_round(client: Client, round_id: str) -> dict | None:
    result = client.table("rounds").select("*, tees(rating, slope)").eq("id", round_id).execute()
    return result.data[0] if result.data else None


def get_rounds(client: Client, user_id: str, status: str = None, limit: int = 20) -> list[dict]:
    query = client.table("rounds").select("*, courses(name), tees(tee_name)").eq("user_id", user_id)
    if status:
        query = query.eq("status", status)
    return query.order("date", desc=True).limit(limit).execute().data


def get_in_progress_round(client: Client, user_id: str) -> dict | None:
    result = (
        client.table("rounds")
        .select("*, courses(name), tees(tee_name)")
        .eq("user_id", user_id)
        .eq("status", "in_progress")
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def complete_round(client: Client, round_id: str) -> dict:
    """Compute total_score and differential, mark round complete."""
    round_data = get_round(client, round_id)
    hole_scores = get_hole_scores(client, round_id)
    total_score = sum(h["score"] for h in hole_scores)

    differential = None
    if round_data["holes_played"] == "full":
        rating = round_data["tees"]["rating"]
        slope = round_data["tees"]["slope"]
        differential = round((113 / slope) * (total_score - rating), 2)

    result = client.table("rounds").update({
        "status": "complete",
        "total_score": total_score,
        "differential": differential,
    }).eq("id", round_id).execute()
    return result.data[0]


def update_round(client: Client, round_id: str, **kwargs) -> dict:
    result = client.table("rounds").update(kwargs).eq("id", round_id).execute()
    return result.data[0]


def delete_round(client: Client, round_id: str):
    client.table("rounds").delete().eq("id", round_id).execute()


# ─────────────────────────────────────────────
# HOLE SCORES
# ─────────────────────────────────────────────

def upsert_hole_score(
    client: Client,
    round_id: str,
    hole_number: int,
    score: int,
    putts: int,
    fairway_hit: str,
    green_in_regulation: bool,
    penalties: int,
) -> dict:
    result = client.table("hole_scores").upsert({
        "round_id": round_id,
        "hole_number": hole_number,
        "score": score,
        "putts": putts,
        "fairway_hit": fairway_hit,
        "green_in_regulation": green_in_regulation,
        "penalties": penalties,
    }, on_conflict="round_id,hole_number").execute()
    return result.data[0]


def get_hole_scores(client: Client, round_id: str) -> list[dict]:
    return (
        client.table("hole_scores")
        .select("*")
        .eq("round_id", round_id)
        .order("hole_number")
        .execute()
        .data
    )


def get_hole_score(client: Client, hole_score_id: str) -> dict | None:
    result = client.table("hole_scores").select("*").eq("id", hole_score_id).execute()
    return result.data[0] if result.data else None
```

- [ ] **Step 4: Run all db tests**

```bash
pytest tests/test_db.py -v
```

Expected: All tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/db.py tests/test_db.py
git commit -m "feat: add data layer for rounds and hole scores"
```

---

## Task 7: Data Layer — Shots & User Bag

**Files:**
- Modify: `src/db.py` (add shots and user_bag functions)
- Modify: `tests/test_db.py`

- [ ] **Step 1: Add failing tests**

```python
# Add to tests/test_db.py
from src.db import create_shot, get_shots, delete_shots_for_hole, get_user_bag, set_user_bag

def test_create_shot(mocker):
    client = make_mock_client()
    client.table.return_value.insert.return_value.execute.return_value.data = [
        {"id": "s1", "shot_number": 1, "club": "7i", "outcome": "green"}
    ]
    result = create_shot(client, hole_score_id="hs1", shot_number=1,
                         distance_to_hole=150, club="7i", shot_type="fairway",
                         lie="good", contact=["good"], miss_direction=None,
                         outcome="green", penalty_reason=None, distance_hit=145)
    assert result["club"] == "7i"


def test_get_user_bag(mocker):
    client = make_mock_client()
    client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = [
        {"club": "Driver"}, {"club": "7i"}, {"club": "PW"}
    ]
    result = get_user_bag(client, user_id="u1")
    assert "Driver" in result
    assert len(result) == 3


def test_set_user_bag_replaces_existing(mocker):
    client = make_mock_client()
    client.table.return_value.delete.return_value.eq.return_value.execute.return_value.data = []
    client.table.return_value.insert.return_value.execute.return_value.data = [
        {"club": "Driver"}, {"club": "7i"}
    ]
    set_user_bag(client, user_id="u1", clubs=["Driver", "7i"])
    client.table.return_value.delete.assert_called()
    client.table.return_value.insert.assert_called()
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/test_db.py::test_create_shot tests/test_db.py::test_get_user_bag -v
```

- [ ] **Step 3: Add shots and user_bag to src/db.py**

```python
# Add to src/db.py

# ─────────────────────────────────────────────
# SHOTS
# ─────────────────────────────────────────────

def create_shot(
    client: Client,
    hole_score_id: str,
    shot_number: int,
    distance_to_hole: int | None,
    club: str,
    shot_type: str,
    lie: str,
    contact: list[str],
    miss_direction: str | None,
    outcome: str,
    penalty_reason: str | None,
    distance_hit: int | None = None,
) -> dict:
    result = client.table("shots").insert({
        "hole_score_id": hole_score_id,
        "shot_number": shot_number,
        "distance_to_hole": distance_to_hole,
        "club": club,
        "shot_type": shot_type,
        "lie": lie,
        "contact": contact,
        "miss_direction": miss_direction,
        "outcome": outcome,
        "penalty_reason": penalty_reason,
        "distance_hit": distance_hit,
    }).execute()
    return result.data[0]


def get_shots(client: Client, hole_score_id: str) -> list[dict]:
    return (
        client.table("shots")
        .select("*")
        .eq("hole_score_id", hole_score_id)
        .order("shot_number")
        .execute()
        .data
    )


def update_shot(client: Client, shot_id: str, **kwargs) -> dict:
    result = client.table("shots").update(kwargs).eq("id", shot_id).execute()
    return result.data[0]


def delete_shot(client: Client, shot_id: str):
    client.table("shots").delete().eq("id", shot_id).execute()


def delete_shots_for_hole(client: Client, hole_score_id: str):
    client.table("shots").delete().eq("hole_score_id", hole_score_id).execute()


# ─────────────────────────────────────────────
# USER BAG
# ─────────────────────────────────────────────

def get_user_bag(client: Client, user_id: str) -> list[str]:
    """Return list of club names in the user's bag."""
    result = (
        client.table("user_bag")
        .select("club")
        .eq("user_id", user_id)
        .order("club")
        .execute()
    )
    return [row["club"] for row in result.data]


def set_user_bag(client: Client, user_id: str, clubs: list[str]):
    """Replace the user's entire bag with the given club list."""
    client.table("user_bag").delete().eq("user_id", user_id).execute()
    if clubs:
        rows = [{"user_id": user_id, "club": club} for club in clubs]
        client.table("user_bag").insert(rows).execute()
```

- [ ] **Step 4: Run all db tests**

```bash
pytest tests/test_db.py -v
```

Expected: All tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/db.py tests/test_db.py
git commit -m "feat: add data layer for shots and user bag"
```

---

## Task 8: Analytics — Metrics & Benchmarks

**Files:**
- Create: `src/analytics.py`
- Create: `tests/test_analytics.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_analytics.py
import pandas as pd
import pytest
from src.analytics import (
    compute_user_metrics,
    interpolate_benchmark,
    normalize_metric_gap,
)


def make_hole_scores(n_rounds=5, putts_per_hole=2, gir=True, fairway="yes", penalties=0):
    rows = []
    for r in range(n_rounds):
        for h in range(1, 19):
            rows.append({
                "round_id": f"r{r}",
                "hole_number": h,
                "score": 4,
                "putts": putts_per_hole,
                "fairway_hit": fairway,
                "green_in_regulation": gir,
                "penalties": penalties,
            })
    return pd.DataFrame(rows)


def make_rounds(n=5, avg_score=90):
    return pd.DataFrame([
        {"id": f"r{i}", "total_score": avg_score, "holes_played": "full"}
        for i in range(n)
    ])


def test_compute_user_metrics_putts():
    rounds_df = make_rounds(5)
    hole_scores_df = make_hole_scores(5, putts_per_hole=2)
    metrics = compute_user_metrics(rounds_df, hole_scores_df, pd.DataFrame())
    assert metrics["putts_per_round"] == pytest.approx(36.0)


def test_compute_user_metrics_gir_pct():
    rounds_df = make_rounds(5)
    hole_scores_df = make_hole_scores(5, gir=True)
    metrics = compute_user_metrics(rounds_df, hole_scores_df, pd.DataFrame())
    assert metrics["gir_pct"] == pytest.approx(1.0)


def test_compute_user_metrics_fairways_hit_pct():
    rounds_df = make_rounds(5)
    hole_scores_df = make_hole_scores(5, fairway="yes")
    metrics = compute_user_metrics(rounds_df, hole_scores_df, pd.DataFrame())
    assert metrics["fairways_hit_pct"] == pytest.approx(1.0)


def test_interpolate_benchmark_scratch():
    target = interpolate_benchmark(avg_score=72)
    assert target["putts_per_round"] == pytest.approx(29.0)
    assert target["gir_pct"] == pytest.approx(0.67)


def test_interpolate_benchmark_bogey():
    target = interpolate_benchmark(avg_score=95)
    assert target["putts_per_round"] == pytest.approx(36.0)


def test_interpolate_benchmark_midpoint():
    # Score halfway between 72 and 95 (~83.5) should be midpoint values
    target = interpolate_benchmark(avg_score=83.5)
    assert target["putts_per_round"] == pytest.approx((29 + 36) / 2, rel=0.05)


def test_interpolate_benchmark_clamps_below_scratch():
    target = interpolate_benchmark(avg_score=65)
    assert target["putts_per_round"] == pytest.approx(29.0)


def test_interpolate_benchmark_clamps_above_bogey():
    target = interpolate_benchmark(avg_score=110)
    assert target["putts_per_round"] == pytest.approx(36.0)


def test_normalize_metric_gap_higher_is_worse():
    # putts: user has 38, target is 33 → positive gap (worse)
    gap = normalize_metric_gap("putts_per_round", user_value=38, target_value=33)
    assert gap > 0


def test_normalize_metric_gap_higher_is_better():
    # gir_pct: user has 0.20, target is 0.35 → positive gap (worse)
    gap = normalize_metric_gap("gir_pct", user_value=0.20, target_value=0.35)
    assert gap > 0
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/test_analytics.py -v
```

Expected: ImportError.

- [ ] **Step 3: Write src/analytics.py — metrics and benchmarks**

```python
# src/analytics.py
import pandas as pd
import numpy as np
from src.constants import BENCHMARKS

# Metrics where a LOWER value is better
LOWER_IS_BETTER = {"putts_per_round", "penalties_per_round",
                   "scoring_avg_par3", "scoring_avg_par4", "scoring_avg_par5"}
# Metrics where a HIGHER value is better
HIGHER_IS_BETTER = {"gir_pct", "fairways_hit_pct"}

METRIC_DISPLAY_NAMES = {
    "putts_per_round": "Putting",
    "gir_pct": "Approach Play (GIR)",
    "fairways_hit_pct": "Driving Accuracy",
    "penalties_per_round": "Penalty Avoidance",
    "scoring_avg_par3": "Par 3 Scoring",
    "scoring_avg_par4": "Par 4 Scoring",
    "scoring_avg_par5": "Par 5 Scoring",
}


def compute_user_metrics(
    rounds_df: pd.DataFrame,
    hole_scores_df: pd.DataFrame,
    shots_df: pd.DataFrame,
) -> dict:
    """Compute average metrics across the provided rounds."""
    if rounds_df.empty or hole_scores_df.empty:
        return {}

    round_ids = rounds_df["id"].tolist()
    hs = hole_scores_df[hole_scores_df["round_id"].isin(round_ids)]

    n_rounds = len(round_ids)
    metrics = {}

    # Putts per round
    metrics["putts_per_round"] = hs.groupby("round_id")["putts"].sum().mean()

    # GIR %
    metrics["gir_pct"] = hs["green_in_regulation"].mean()

    # Fairways hit % (exclude 'na' holes — par 3s)
    fairway_holes = hs[hs["fairway_hit"] != "na"]
    if not fairway_holes.empty:
        metrics["fairways_hit_pct"] = (fairway_holes["fairway_hit"] == "yes").mean()
    else:
        metrics["fairways_hit_pct"] = None

    # Penalties per round
    metrics["penalties_per_round"] = hs.groupby("round_id")["penalties"].sum().mean()

    # Avg score by par type — requires par per hole from course
    # This requires hole-level par data joined in by the caller
    # If par column exists in hole_scores_df, compute it
    if "par" in hs.columns:
        for par in [3, 4, 5]:
            par_holes = hs[hs["par"] == par]
            if not par_holes.empty:
                metrics[f"scoring_avg_par{par}"] = par_holes["score"].mean()

    # Recent avg score (used for benchmark interpolation)
    if "total_score" in rounds_df.columns:
        metrics["avg_score"] = rounds_df["total_score"].mean()

    return metrics


def interpolate_benchmark(avg_score: float) -> dict:
    """
    Linearly interpolate between scratch and bogey benchmarks
    based on the user's average score. Clamps outside [72, 95].
    """
    scratch = BENCHMARKS["scratch"]
    bogey = BENCHMARKS["bogey"]
    scratch_score = scratch["avg_score"]  # 72
    bogey_score = bogey["avg_score"]      # 95

    # Clamp
    clamped = max(scratch_score, min(bogey_score, avg_score))
    t = (clamped - scratch_score) / (bogey_score - scratch_score)  # 0=scratch, 1=bogey

    target = {}
    for metric in scratch:
        if metric == "avg_score":
            continue
        target[metric] = scratch[metric] + t * (bogey[metric] - scratch[metric])
    return target


def normalize_metric_gap(metric: str, user_value: float, target_value: float) -> float:
    """
    Return a positive gap when the user is WORSE than the target.
    Normalizes by the full scratch-to-bogey range so metrics are comparable.
    """
    scratch_val = BENCHMARKS["scratch"][metric]
    bogey_val = BENCHMARKS["bogey"][metric]
    full_range = abs(bogey_val - scratch_val) or 1.0

    if metric in LOWER_IS_BETTER:
        raw_gap = user_value - target_value  # positive = user is worse
    else:
        raw_gap = target_value - user_value  # positive = user is worse

    return raw_gap / full_range
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_analytics.py -v
```

Expected: All tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/analytics.py tests/test_analytics.py
git commit -m "feat: add analytics layer - metrics computation and benchmark interpolation"
```

---

## Task 9: Analytics — Focus Areas

**Files:**
- Modify: `src/analytics.py` (add focus area logic)
- Modify: `tests/test_analytics.py`

- [ ] **Step 1: Write failing tests**

```python
# Add to tests/test_analytics.py
from src.analytics import rank_focus_areas, get_shot_pattern_insight

def test_rank_focus_areas_returns_top_2():
    user_metrics = {
        "avg_score": 95,
        "putts_per_round": 38,
        "gir_pct": 0.20,
        "fairways_hit_pct": 0.55,
        "penalties_per_round": 2.0,
    }
    focus_areas = rank_focus_areas(user_metrics, n=2)
    assert len(focus_areas) == 2
    # Each focus area has a metric name and gap score
    assert "metric" in focus_areas[0]
    assert "gap_score" in focus_areas[0]
    assert focus_areas[0]["gap_score"] >= focus_areas[1]["gap_score"]


def test_rank_focus_areas_ignores_none_metrics():
    user_metrics = {
        "avg_score": 90,
        "putts_per_round": 34,
        "gir_pct": None,  # not enough data
        "fairways_hit_pct": 0.45,
    }
    focus_areas = rank_focus_areas(user_metrics, n=2)
    metrics_returned = [fa["metric"] for fa in focus_areas]
    assert "gir_pct" not in metrics_returned


def test_shot_pattern_insight_miss_direction():
    shots_df = pd.DataFrame([
        {"outcome": "other", "miss_direction": "left", "hole_score_id": "h1"},
        {"outcome": "other", "miss_direction": "left", "hole_score_id": "h2"},
        {"outcome": "other", "miss_direction": "right", "hole_score_id": "h3"},
        {"outcome": "green", "miss_direction": None, "hole_score_id": "h4"},
    ])
    hole_scores_df = pd.DataFrame([
        {"id": "h1", "fairway_hit": "no"},
        {"id": "h2", "fairway_hit": "no"},
        {"id": "h3", "fairway_hit": "no"},
        {"id": "h4", "fairway_hit": "yes"},
    ])
    insight = get_shot_pattern_insight("fairways_hit_pct", shots_df, hole_scores_df)
    assert insight is not None
    assert "left" in insight.lower()
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/test_analytics.py::test_rank_focus_areas_returns_top_2 -v
```

- [ ] **Step 3: Add focus area logic to src/analytics.py**

```python
# Add to src/analytics.py

def rank_focus_areas(user_metrics: dict, n: int = 2) -> list[dict]:
    """
    Rank metrics by weighted gap vs interpolated benchmark.
    Returns top n focus areas sorted by gap score (highest = most impactful).
    """
    avg_score = user_metrics.get("avg_score", 90)
    target = interpolate_benchmark(avg_score)

    ranked = []
    for metric, target_value in target.items():
        user_value = user_metrics.get(metric)
        if user_value is None:
            continue
        gap = normalize_metric_gap(metric, user_value, target_value)
        if gap <= 0:
            continue  # User is already at or better than target
        ranked.append({
            "metric": metric,
            "display_name": METRIC_DISPLAY_NAMES.get(metric, metric),
            "user_value": user_value,
            "target_value": target_value,
            "gap_score": gap,
        })

    ranked.sort(key=lambda x: x["gap_score"], reverse=True)
    return ranked[:n]


def get_shot_pattern_insight(
    metric: str,
    shots_df: pd.DataFrame,
    hole_scores_df: pd.DataFrame,
) -> str | None:
    """
    Generate a plain-English sub-bullet for a focus area using shot data.
    Returns None if not enough data or no clear pattern.
    """
    if shots_df.empty:
        return None

    if metric == "fairways_hit_pct":
        # Look at miss direction on tee shots
        tee_shots = shots_df[shots_df.get("shot_type", pd.Series()) == "tee"] if "shot_type" in shots_df.columns else shots_df
        missed = tee_shots[tee_shots["miss_direction"].notna()]
        if len(missed) < 5:
            return None
        left_pct = (missed["miss_direction"] == "left").mean()
        right_pct = (missed["miss_direction"] == "right").mean()
        dominant = "left" if left_pct > right_pct else "right"
        dominant_pct = max(left_pct, right_pct)
        if dominant_pct >= 0.6:
            return f"{dominant_pct:.0%} of missed fairways go {dominant} — suggests a consistent {'pull/hook' if dominant == 'left' else 'push/slice'} pattern"

    elif metric == "gir_pct":
        missed_green_shots = shots_df[
            shots_df["miss_direction"].notna()
        ] if "miss_direction" in shots_df.columns else pd.DataFrame()
        if len(missed_green_shots) < 5:
            return None
        left_pct = (missed_green_shots["miss_direction"] == "left").mean()
        right_pct = (missed_green_shots["miss_direction"] == "right").mean()
        dominant = "left" if left_pct > right_pct else "right"
        dominant_pct = max(left_pct, right_pct)
        if dominant_pct >= 0.55:
            return f"{dominant_pct:.0%} of approach misses go {dominant} — consistent ball flight issue on approach shots"

    elif metric == "putts_per_round":
        return "Consider tracking individual putts to identify whether the issue is distance control or short putting"

    return None


def build_focus_area_cards(
    user_metrics: dict,
    shots_df: pd.DataFrame,
    hole_scores_df: pd.DataFrame,
    n_shot_rounds: int = 0,
) -> list[dict]:
    """
    Return a list of focus area dicts ready to render.
    Each dict has: display_name, user_value, target_value, insight (or None).
    """
    areas = rank_focus_areas(user_metrics, n=2)
    min_shot_rounds = 3

    for area in areas:
        if n_shot_rounds >= min_shot_rounds:
            area["insight"] = get_shot_pattern_insight(
                area["metric"], shots_df, hole_scores_df
            )
        else:
            area["insight"] = None
    return areas
```

- [ ] **Step 4: Run all analytics tests**

```bash
pytest tests/test_analytics.py -v
```

Expected: All tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/analytics.py tests/test_analytics.py
git commit -m "feat: add focus area ranking and shot pattern insight logic"
```

---

## Task 10: Dashboard Page

**Files:**
- Create: `pages/1_Dashboard.py`

- [ ] **Step 1: Create pages/1_Dashboard.py**

```python
# pages/1_Dashboard.py
import streamlit as st
import pandas as pd
import plotly.express as px
from src.auth import require_auth, get_current_user_id, get_supabase_client
from src.db import get_rounds, get_hole_scores, get_in_progress_round
from src.analytics import compute_user_metrics, build_focus_area_cards, METRIC_DISPLAY_NAMES
from src.constants import BENCHMARKS

require_auth()

st.title("Dashboard")

client = get_supabase_client()
user_id = get_current_user_id()

# ── In-Progress Round Banner ──────────────────
in_progress = get_in_progress_round(client, user_id)
if in_progress:
    course_name = in_progress.get("courses", {}).get("name", "Unknown Course")
    st.warning(f"Round in progress: **{course_name}** on {in_progress['date']}")
    if st.button("Continue Round"):
        st.session_state["active_round_id"] = in_progress["id"]
        st.switch_page("pages/2_New_Round.py")

# ── Load data ──────────────────────────────────
rounds = get_rounds(client, user_id, status="complete", limit=20)
rounds_df = pd.DataFrame(rounds) if rounds else pd.DataFrame()

if rounds_df.empty:
    st.info("No rounds logged yet. Start a new round to see your stats here.")
    if st.button("Start New Round"):
        st.switch_page("pages/2_New_Round.py")
    st.stop()

# Load all hole scores for these rounds
all_hole_scores = []
for r in rounds:
    all_hole_scores.extend(get_hole_scores(client, r["id"]))
hole_scores_df = pd.DataFrame(all_hole_scores) if all_hole_scores else pd.DataFrame()

user_metrics = compute_user_metrics(rounds_df, hole_scores_df, pd.DataFrame())
n_shot_rounds = 0  # Shot data integration: count rounds with shots (Task 13 enhancement)

# ── Focus Areas Card ──────────────────────────
st.subheader("Focus Areas")
focus_areas = build_focus_area_cards(user_metrics, pd.DataFrame(), hole_scores_df, n_shot_rounds)

if not focus_areas:
    st.info("Not enough data yet to identify focus areas. Log a few more rounds.")
else:
    cols = st.columns(len(focus_areas))
    for col, area in zip(cols, focus_areas):
        with col:
            with st.container(border=True):
                st.markdown(f"### {area['display_name']}")
                # Format value for display
                val = area["user_value"]
                target = area["target_value"]
                if area["metric"].endswith("_pct"):
                    st.metric(label="Your average", value=f"{val:.1%}", delta=f"{val - target:.1%} vs target", delta_color="inverse")
                else:
                    st.metric(label="Your average", value=f"{val:.1f}", delta=f"{val - target:+.1f} vs target", delta_color="inverse")
                if area.get("insight"):
                    st.caption(area["insight"])

st.divider()

# ── Scoring Trend ─────────────────────────────
st.subheader("Scoring Trend")
fig = px.line(
    rounds_df.sort_values("date"),
    x="date",
    y="total_score",
    markers=True,
    labels={"total_score": "Score", "date": "Date"},
    title="Score per Round (last 20)",
)
fig.update_traces(line_color="#2ecc71")
st.plotly_chart(fig, use_container_width=True)

# ── Key Stat Trends ───────────────────────────
st.subheader("Key Stats")
stat_cols = st.columns(3)
with stat_cols[0]:
    putts = hole_scores_df.groupby("round_id")["putts"].sum().mean()
    st.metric("Avg Putts / Round", f"{putts:.1f}", help="Lower is better. Bogey avg: 36")
with stat_cols[1]:
    gir = hole_scores_df["green_in_regulation"].mean()
    st.metric("GIR %", f"{gir:.1%}", help="Higher is better. Bogey avg: 25%")
with stat_cols[2]:
    fw = hole_scores_df[hole_scores_df["fairway_hit"] != "na"]
    fw_pct = (fw["fairway_hit"] == "yes").mean() if not fw.empty else 0
    st.metric("Fairways Hit %", f"{fw_pct:.1%}", help="Higher is better. Bogey avg: 40%")
```

- [ ] **Step 2: Manually test the dashboard**

```bash
streamlit run app.py
```

1. Log in
2. Navigate to Dashboard
3. With no rounds: confirm "No rounds logged yet" message appears
4. Confirm "Start New Round" button is visible

- [ ] **Step 3: Commit**

```bash
git add pages/1_Dashboard.py
git commit -m "feat: add dashboard page with focus areas, scoring trend, and key stats"
```

---

## Task 11: New Round — Setup Flow

**Files:**
- Create: `pages/2_New_Round.py`

- [ ] **Step 1: Create the round setup section (course + tee + holes selection)**

```python
# pages/2_New_Round.py
import streamlit as st
from datetime import date
from src.auth import require_auth, get_current_user_id, get_supabase_client
from src.db import (
    get_courses, get_tees, create_round, get_round,
    get_hole_scores, upsert_hole_score, complete_round, create_course, create_tee
)
from src.constants import HOLES_PLAYED_OPTIONS, HOLES_FOR_ROUND

require_auth()

client = get_supabase_client()
user_id = get_current_user_id()

# Initialize session state for round flow
if "round_step" not in st.session_state:
    st.session_state.round_step = "setup"  # setup | playing | complete
if "active_round_id" not in st.session_state:
    st.session_state.active_round_id = None
if "current_hole_idx" not in st.session_state:
    st.session_state.current_hole_idx = 0

st.title("New Round")

# ── STEP: SETUP ───────────────────────────────
if st.session_state.round_step == "setup":
    st.subheader("Round Setup")

    # Course search and selection
    search = st.text_input("Search courses", placeholder="Type a course name...")
    courses = get_courses(client, search=search if search else None)

    if not courses:
        st.info("No courses found. Add one below.")
    else:
        course_options = {f"{c['name']} — {c['city']}, {c['state']}": c["id"] for c in courses}
        selected_course_label = st.selectbox("Select course", options=list(course_options.keys()))
        selected_course_id = course_options[selected_course_label]

    # Add new course expander
    with st.expander("+ Add a new course"):
        with st.form("add_course_form"):
            new_name = st.text_input("Course name")
            col1, col2 = st.columns(2)
            new_city = col1.text_input("City")
            new_state = col2.text_input("State")
            st.write("Par for each hole (1–18):")
            par_cols = st.columns(9)
            pars = []
            for i in range(18):
                pars.append(par_cols[i % 9].number_input(f"H{i+1}", min_value=3, max_value=6, value=4, key=f"par_{i}"))
            add_course_submitted = st.form_submit_button("Add Course")
            if add_course_submitted:
                if new_name and new_city and new_state:
                    create_course(client, user_id, new_name, new_city, new_state, pars)
                    st.success(f"Course '{new_name}' added!")
                    st.rerun()
                else:
                    st.error("Please fill in name, city, and state.")

    # Tee selection (only shown when a course is selected)
    if courses and selected_course_id:
        tees = get_tees(client, course_id=selected_course_id)
        if not tees:
            st.warning("No tees set up for this course yet. Add one below.")
            tee_id = None
        else:
            tee_options = {f"{t['tee_name']} (Rating: {t['rating']}, Slope: {t['slope']})": t["id"] for t in tees}
            selected_tee_label = st.selectbox("Select tee", options=list(tee_options.keys()))
            tee_id = tee_options[selected_tee_label]

        # Add tee expander
        with st.expander("+ Add a tee for this course"):
            with st.form("add_tee_form"):
                tee_name = st.text_input("Tee name (e.g. Blue, White)")
                col1, col2 = st.columns(2)
                rating = col1.number_input("Course rating", min_value=60.0, max_value=80.0, value=72.0, step=0.1)
                slope = col2.number_input("Slope", min_value=55, max_value=155, value=113)
                st.write("Yardage for each hole (1–18):")
                yard_cols = st.columns(9)
                yardages = []
                for i in range(18):
                    yardages.append(yard_cols[i % 9].number_input(f"H{i+1}", min_value=50, max_value=700, value=400, key=f"yd_{i}"))
                add_tee_submitted = st.form_submit_button("Add Tee")
                if add_tee_submitted and tee_name:
                    create_tee(client, user_id, selected_course_id, tee_name, rating, slope, yardages)
                    st.success(f"Tee '{tee_name}' added!")
                    st.rerun()

    # Holes played + date
    holes_label = st.selectbox("Holes played", options=list(HOLES_PLAYED_OPTIONS.keys()))
    round_date = st.date_input("Date", value=date.today())
    notes = st.text_area("Notes (optional)", height=68)

    if st.button("Start Round", type="primary", disabled=(not courses or not tee_id)):
        new_round = create_round(
            client, user_id,
            course_id=selected_course_id,
            tee_id=tee_id,
            date=str(round_date),
            holes_played=HOLES_PLAYED_OPTIONS[holes_label],
            notes=notes or None,
        )
        st.session_state.active_round_id = new_round["id"]
        st.session_state.round_step = "playing"
        st.session_state.current_hole_idx = 0
        st.rerun()
```

- [ ] **Step 2: Manually test the setup flow**

```bash
streamlit run app.py
```

1. Navigate to New Round
2. Search for a course — confirm search works
3. Add a new course with tees
4. Select course and tee, click Start Round
5. Confirm session state transitions to "playing"

- [ ] **Step 3: Commit**

```bash
git add pages/2_New_Round.py
git commit -m "feat: add new round setup flow - course/tee selection and round creation"
```

---

## Task 12: New Round — Hole-by-Hole Entry

**Files:**
- Modify: `pages/2_New_Round.py`

- [ ] **Step 1: Add hole entry UI to 2_New_Round.py**

Add the following below the setup block in `pages/2_New_Round.py`:

```python
# ── STEP: PLAYING ─────────────────────────────
elif st.session_state.round_step == "playing":
    round_id = st.session_state.active_round_id
    round_data = get_round(client, round_id)

    if round_data is None:
        st.error("Round not found. Please start a new round.")
        st.session_state.round_step = "setup"
        st.rerun()

    holes = HOLES_FOR_ROUND[round_data["holes_played"]]
    total_holes = len(holes)
    hole_idx = st.session_state.current_hole_idx
    hole_number = holes[hole_idx]

    # Load course data for par/yardage
    from src.db import get_course, get_tee
    course = get_course(client, round_data["course_id"])
    tee = get_tee(client, round_data["tee_id"])
    par = course["par_per_hole"][hole_number - 1]
    yardage = tee["yardage_per_hole"][hole_number - 1]

    # Progress indicator
    st.progress((hole_idx) / total_holes, text=f"Hole {hole_idx + 1} of {total_holes}")
    st.subheader(f"Hole {hole_number} — Par {par} — {yardage} yards")

    # Load existing data for this hole (if returning mid-round)
    existing_scores = get_hole_scores(client, round_id)
    existing = next((h for h in existing_scores if h["hole_number"] == hole_number), None)

    # Validation rules (from spec):
    # score: 1-15 (warn if >10, don't block)
    # putts: 0-6, must not exceed score
    # penalties: 0-score

    with st.form(f"hole_{hole_number}_form"):
        col1, col2, col3 = st.columns(3)

        score = col1.number_input(
            "Score", min_value=1, max_value=15,
            value=existing["score"] if existing else par,
        )
        if score > 10:
            st.warning("Score > 10 — are you sure?")

        putts = col2.number_input(
            "Putts", min_value=0, max_value=6,
            value=existing["putts"] if existing else 2,
        )

        penalties = col3.number_input(
            "Penalties", min_value=0, max_value=10,
            value=existing["penalties"] if existing else 0,
        )

        col4, col5 = st.columns(2)
        fairway_options = ["yes", "no", "na"]
        default_fairway = existing["fairway_hit"] if existing else ("na" if par == 3 else "yes")
        fairway_hit = col4.selectbox(
            "Fairway hit", options=fairway_options,
            index=fairway_options.index(default_fairway),
        )

        gir = col5.checkbox(
            "Green in regulation",
            value=existing["green_in_regulation"] if existing else False,
        )

        # Validation warning
        if putts > score:
            st.error("Putts cannot exceed score.")

        col_prev, col_next = st.columns(2)
        prev_clicked = col_prev.form_submit_button("← Previous", disabled=(hole_idx == 0))
        next_label = "Finish Round →" if hole_idx == total_holes - 1 else "Next Hole →"
        next_clicked = col_next.form_submit_button(next_label, type="primary")

        if next_clicked or prev_clicked:
            if putts > score:
                st.error("Cannot save: putts exceed score.")
                st.stop()

            # Save this hole immediately
            upsert_hole_score(
                client, round_id, hole_number,
                score=int(score), putts=int(putts),
                fairway_hit=fairway_hit,
                green_in_regulation=gir,
                penalties=int(penalties),
            )

            if next_clicked:
                if hole_idx == total_holes - 1:
                    # Last hole — complete the round
                    complete_round(client, round_id)
                    st.session_state.round_step = "complete"
                else:
                    st.session_state.current_hole_idx += 1
            elif prev_clicked:
                st.session_state.current_hole_idx -= 1

            st.rerun()

# ── STEP: COMPLETE ────────────────────────────
elif st.session_state.round_step == "complete":
    round_id = st.session_state.active_round_id
    round_data = get_round(client, round_id)
    st.success(f"Round complete! Total score: **{round_data['total_score']}**")
    if round_data.get("differential") is not None:
        st.write(f"Differential: {round_data['differential']:.1f}")

    col1, col2 = st.columns(2)
    if col1.button("View Round Summary"):
        st.session_state.selected_round_id = round_id
        st.switch_page("pages/3_Round_History.py")
    if col2.button("Back to Dashboard"):
        # Reset round state
        st.session_state.round_step = "setup"
        st.session_state.active_round_id = None
        st.session_state.current_hole_idx = 0
        st.switch_page("pages/1_Dashboard.py")
```

- [ ] **Step 2: Manually test hole entry**

```bash
streamlit run app.py
```

1. Start a new round with a course that has tees set up
2. Enter scores for holes 1-3, click Next each time
3. Close the browser tab mid-round
4. Reopen the app — confirm the Dashboard shows "Continue Round"
5. Continue round — confirm it resumes on the next unplayed hole
6. Complete all holes — confirm the completion screen shows total score

- [ ] **Step 3: Commit**

```bash
git add pages/2_New_Round.py
git commit -m "feat: add hole-by-hole entry with persistent save and round completion"
```

---

## Task 13: New Round — Shot Tracking

**Files:**
- Modify: `pages/2_New_Round.py` (add shot tracking expander to each hole)

- [ ] **Step 1: Add shot entry expander inside the hole form**

Inside the `with st.form(f"hole_{hole_number}_form"):` block in Task 12, add after the GIR checkbox:

```python
        # Shot tracking (outside the form — forms don't support dynamic rows)
        # Note: shots are saved separately, not as part of the hole form submit
```

Then, **after** the `st.form` block (outside it), add:

```python
    # Shot tracking (separate from the hole score form to allow dynamic rows)
    with st.expander("Track Shots (optional)"):
        from src.db import get_shots, create_shot, delete_shots_for_hole, get_user_bag
        from src.constants import (
            ALL_CLUBS, SHOT_TYPE_OPTIONS, LIE_OPTIONS,
            CONTACT_OPTIONS, OUTCOME_OPTIONS, PENALTY_REASON_OPTIONS
        )

        # Get user's bag for club selector
        user_bag = get_user_bag(client, user_id)
        club_options = user_bag if user_bag else ALL_CLUBS

        # Load existing shots for this hole (if hole score exists)
        if existing:
            existing_shots = get_shots(client, existing["id"])
            st.write(f"{len(existing_shots)} shot(s) tracked for this hole.")

        st.write("**Add shots one at a time:**")
        with st.form(f"shot_form_{hole_number}"):
            s_col1, s_col2, s_col3 = st.columns(3)
            shot_club = s_col1.selectbox("Club", options=club_options)
            shot_type = s_col2.selectbox("Shot type (lie location)", options=SHOT_TYPE_OPTIONS)
            lie = s_col3.selectbox("Lie quality", options=LIE_OPTIONS)

            s_col4, s_col5, s_col6 = st.columns(3)
            distance_to_hole = s_col4.number_input("Distance to hole (yds)", min_value=0, max_value=600, value=150)
            distance_hit = s_col5.number_input("Distance hit (yds, optional)", min_value=0, max_value=400, value=0)
            outcome = s_col6.selectbox("Outcome", options=OUTCOME_OPTIONS)

            contact = st.multiselect("Contact (select all that apply)", options=CONTACT_OPTIONS, default=["good"])
            miss_direction = st.selectbox("Miss direction (if applicable)", options=["none", "left", "right"])
            penalty_reason = None
            if outcome == "penalty":
                penalty_reason = st.selectbox("Penalty reason", options=PENALTY_REASON_OPTIONS)

            add_shot = st.form_submit_button("Add Shot")
            if add_shot and existing:
                shot_num = len(existing_shots) + 1 if existing else 1
                create_shot(
                    client,
                    hole_score_id=existing["id"],
                    shot_number=shot_num,
                    distance_to_hole=distance_to_hole if distance_to_hole > 0 else None,
                    club=shot_club,
                    shot_type=shot_type,
                    lie=lie,
                    contact=contact,
                    miss_direction=miss_direction if miss_direction != "none" else None,
                    outcome=outcome,
                    penalty_reason=penalty_reason,
                    distance_hit=distance_hit if distance_hit > 0 else None,
                )
                st.success("Shot added!")
                st.rerun()
            elif add_shot and not existing:
                st.warning("Save the hole score first (click Next Hole), then come back to add shots.")
```

- [ ] **Step 2: Manually test shot tracking**

1. Enter a hole score and click Next to save it
2. Use browser back or re-navigate to add shots to a saved hole
3. Add 2-3 shots — confirm they appear in the expander
4. Confirm shot with `outcome = penalty` shows penalty reason dropdown

- [ ] **Step 3: Commit**

```bash
git add pages/2_New_Round.py
git commit -m "feat: add optional shot tracking to hole entry"
```

---

## Task 14: Round History Page

**Files:**
- Create: `pages/3_Round_History.py`

- [ ] **Step 1: Create pages/3_Round_History.py**

```python
# pages/3_Round_History.py
import streamlit as st
import pandas as pd
from src.auth import require_auth, get_current_user_id, get_supabase_client
from src.db import (
    get_rounds, get_round, get_hole_scores, get_shots,
    upsert_hole_score, complete_round, get_course, get_tee
)

require_auth()

client = get_supabase_client()
user_id = get_current_user_id()

st.title("Round History")

rounds = get_rounds(client, user_id, status="complete", limit=50)

if not rounds:
    st.info("No completed rounds yet.")
    st.stop()

# ── Round List ────────────────────────────────
rounds_df = pd.DataFrame(rounds)
rounds_df["course_name"] = rounds_df["courses"].apply(lambda x: x["name"] if x else "Unknown")
rounds_df["tee_name"] = rounds_df["tees"].apply(lambda x: x["tee_name"] if x else "Unknown")

display_df = rounds_df[["date", "course_name", "tee_name", "holes_played", "total_score"]].copy()
display_df.columns = ["Date", "Course", "Tee", "Holes", "Score"]
display_df = display_df.sort_values("Date", ascending=False)

selected_idx = st.dataframe(
    display_df,
    use_container_width=True,
    on_select="rerun",
    selection_mode="single-row",
)

if not selected_idx["selection"]["rows"]:
    st.info("Select a round above to view details.")
    st.stop()

selected_row = display_df.iloc[selected_idx["selection"]["rows"][0]]
selected_round_id = rounds_df.iloc[selected_idx["selection"]["rows"][0]]["id"]

st.divider()
st.subheader(f"{selected_row['Course']} — {selected_row['Date']}")
st.write(f"**Score:** {selected_row['Score']} | **Tee:** {selected_row['Tee']} | **Holes:** {selected_row['Holes']}")

# ── Hole-by-Hole Breakdown ────────────────────
hole_scores = get_hole_scores(client, selected_round_id)
if hole_scores:
    hs_df = pd.DataFrame(hole_scores)[["hole_number", "score", "putts", "fairway_hit", "green_in_regulation", "penalties"]]
    hs_df.columns = ["Hole", "Score", "Putts", "Fairway", "GIR", "Penalties"]
    st.dataframe(hs_df, use_container_width=True, hide_index=True)

# ── Edit Round ────────────────────────────────
with st.expander("Edit this round"):
    st.write("Select a hole to edit:")
    hole_options = {f"Hole {h['hole_number']}": h for h in hole_scores}
    selected_hole_label = st.selectbox("Hole", options=list(hole_options.keys()))
    h = hole_options[selected_hole_label]

    round_data = get_round(client, selected_round_id)
    course = get_course(client, round_data["course_id"])
    par = course["par_per_hole"][h["hole_number"] - 1]

    with st.form("edit_hole_form"):
        col1, col2, col3 = st.columns(3)
        score = col1.number_input("Score", 1, 15, value=h["score"])
        putts = col2.number_input("Putts", 0, 6, value=h["putts"])
        penalties = col3.number_input("Penalties", 0, 10, value=h["penalties"])

        col4, col5 = st.columns(2)
        fw_options = ["yes", "no", "na"]
        fairway_hit = col4.selectbox("Fairway hit", fw_options, index=fw_options.index(h["fairway_hit"]))
        gir = col5.checkbox("Green in regulation", value=h["green_in_regulation"])

        save = st.form_submit_button("Save Changes")
        if save:
            if putts > score:
                st.error("Putts cannot exceed score.")
            else:
                upsert_hole_score(client, selected_round_id, h["hole_number"],
                                  score=score, putts=putts, fairway_hit=fairway_hit,
                                  green_in_regulation=gir, penalties=penalties)
                # Recompute totals
                complete_round(client, selected_round_id)
                st.success("Hole updated!")
                st.rerun()
```

- [ ] **Step 2: Manually test**

1. Log a complete round
2. Navigate to Round History — confirm the round appears
3. Click the round — confirm hole-by-hole breakdown shows
4. Edit a hole score — confirm total recalculates

- [ ] **Step 3: Commit**

```bash
git add pages/3_Round_History.py
git commit -m "feat: add round history page with detail view and hole editing"
```

---

## Task 15: Course Manager Page

**Files:**
- Create: `pages/4_Course_Manager.py`

- [ ] **Step 1: Create pages/4_Course_Manager.py**

```python
# pages/4_Course_Manager.py
import streamlit as st
from src.auth import require_auth, get_current_user_id, get_supabase_client
from src.db import get_courses, get_tees, create_course, create_tee, update_course, delete_course, delete_tee

require_auth()

client = get_supabase_client()
user_id = get_current_user_id()

st.title("Course Manager")

# ── Browse Courses ────────────────────────────
search = st.text_input("Search courses", placeholder="Filter by name...")
courses = get_courses(client, search=search if search else None)

if not courses:
    st.info("No courses found. Add one below.")
else:
    for course in courses:
        with st.expander(f"**{course['name']}** — {course['city']}, {course['state']}"):
            st.write(f"Added by: {course['created_by_user_id'][:8]}...")
            st.write(f"Par: {course['par_per_hole']}")

            tees = get_tees(client, course["id"])
            if tees:
                st.write("**Tees:**")
                for tee in tees:
                    col1, col2 = st.columns([4, 1])
                    col1.write(f"- {tee['tee_name']} | Rating: {tee['rating']} | Slope: {tee['slope']}")
                    if tee["created_by_user_id"] == user_id:
                        if col2.button("Delete", key=f"del_tee_{tee['id']}"):
                            delete_tee(client, tee["id"])
                            st.rerun()
            else:
                st.write("No tees added yet.")

            # Add tee form (only visible for the course creator — or any user in V1)
            with st.form(f"add_tee_{course['id']}"):
                st.write("**Add a tee:**")
                tee_name = st.text_input("Tee name")
                c1, c2 = st.columns(2)
                rating = c1.number_input("Rating", 60.0, 80.0, 72.0, 0.1)
                slope = c2.number_input("Slope", 55, 155, 113)
                st.write("Yardage per hole:")
                yard_cols = st.columns(9)
                yardages = [yard_cols[i % 9].number_input(f"H{i+1}", 50, 700, 400, key=f"yd_{course['id']}_{i}") for i in range(18)]
                if st.form_submit_button("Add Tee") and tee_name:
                    create_tee(client, user_id, course["id"], tee_name, rating, slope, yardages)
                    st.success("Tee added!")
                    st.rerun()

            if course["created_by_user_id"] == user_id:
                # Immutability check: prevent deleting a course that has rounds referencing it
                from src.db import get_rounds
                referencing_rounds = client.table("rounds").select("id").eq("course_id", course["id"]).limit(1).execute()
                if referencing_rounds.data:
                    st.caption("This course has rounds logged against it and cannot be deleted.")
                else:
                    if st.button("Delete Course", key=f"del_course_{course['id']}", type="secondary"):
                        delete_course(client, course["id"])
                        st.rerun()

st.divider()

# ── Add New Course ────────────────────────────
st.subheader("Add a New Course")
with st.form("new_course_form"):
    name = st.text_input("Course name")
    c1, c2 = st.columns(2)
    city = c1.text_input("City")
    state = c2.text_input("State")
    st.write("Par per hole:")
    par_cols = st.columns(9)
    pars = [par_cols[i % 9].number_input(f"H{i+1}", 3, 6, 4, key=f"par_new_{i}") for i in range(18)]
    if st.form_submit_button("Add Course"):
        if name and city and state:
            create_course(client, user_id, name, city, state, pars)
            st.success(f"'{name}' added!")
            st.rerun()
        else:
            st.error("Please fill in name, city, and state.")
```

- [ ] **Step 2: Manually test**

1. Navigate to Course Manager
2. Add a new course with pars
3. Add a tee to the course
4. Search for the course by partial name
5. Delete the tee — confirm it disappears

- [ ] **Step 3: Commit**

```bash
git add pages/4_Course_Manager.py
git commit -m "feat: add course manager page"
```

---

## Task 16: Stats & Analysis Page

**Files:**
- Create: `pages/5_Stats.py`

- [ ] **Step 1: Create pages/5_Stats.py**

```python
# pages/5_Stats.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from src.auth import require_auth, get_current_user_id, get_supabase_client
from src.db import get_rounds, get_hole_scores, get_shots, get_hole_score
from src.analytics import compute_user_metrics, interpolate_benchmark
from src.constants import BENCHMARKS

require_auth()

client = get_supabase_client()
user_id = get_current_user_id()

st.title("Stats & Analysis")

rounds = get_rounds(client, user_id, status="complete", limit=20)
if not rounds:
    st.info("Log some rounds to see stats.")
    st.stop()

rounds_df = pd.DataFrame(rounds)
all_hole_scores = []
for r in rounds:
    all_hole_scores.extend(get_hole_scores(client, r["id"]))
hole_scores_df = pd.DataFrame(all_hole_scores)

user_metrics = compute_user_metrics(rounds_df, hole_scores_df, pd.DataFrame())
avg_score = user_metrics.get("avg_score", 90)
target = interpolate_benchmark(avg_score)

# ── Benchmark Comparison Table ────────────────
st.subheader("Where You Stand")
metric_rows = []
for metric, target_val in target.items():
    user_val = user_metrics.get(metric)
    if user_val is None:
        continue
    scratch_val = BENCHMARKS["scratch"][metric]
    bogey_val = BENCHMARKS["bogey"][metric]
    metric_rows.append({
        "Metric": metric.replace("_", " ").title(),
        "You (last 20)": round(user_val, 2),
        "Your Target": round(target_val, 2),
        "Bogey": round(bogey_val, 2),
        "Scratch": round(scratch_val, 2),
    })
st.dataframe(pd.DataFrame(metric_rows), use_container_width=True, hide_index=True)

st.divider()

# ── Score Distribution ────────────────────────
st.subheader("Score Distribution")
fig = px.histogram(rounds_df, x="total_score", nbins=15,
                   labels={"total_score": "Score"},
                   title="Distribution of Scores")
st.plotly_chart(fig, use_container_width=True)

# ── Stat Trends Over Time ─────────────────────
st.subheader("Stat Trends Over Time")
putts_by_round = hole_scores_df.groupby("round_id")["putts"].sum().reset_index()
putts_by_round = putts_by_round.merge(rounds_df[["id", "date"]], left_on="round_id", right_on="id")

fig2 = px.line(putts_by_round.sort_values("date"), x="date", y="putts",
               markers=True, title="Putts per Round",
               labels={"putts": "Total Putts", "date": "Date"})
st.plotly_chart(fig2, use_container_width=True)

# ── Shot Analysis ─────────────────────────────
st.subheader("Shot Analysis")

# Load shots for all hole scores
all_shots = []
hs_ids = hole_scores_df["id"].tolist() if "id" in hole_scores_df.columns else []
for hs_id in hs_ids[:200]:  # cap to avoid slow loads
    all_shots.extend(get_shots(client, hs_id))

if not all_shots:
    st.info("No shot data tracked yet. Enable shot tracking during a round to see analysis here.")
else:
    shots_df = pd.DataFrame(all_shots)
    # Outcome breakdown by club
    outcome_counts = shots_df.groupby(["club", "outcome"]).size().reset_index(name="count")
    fig3 = px.bar(outcome_counts, x="club", y="count", color="outcome",
                  title="Shot Outcomes by Club",
                  labels={"count": "Shots", "club": "Club"})
    st.plotly_chart(fig3, use_container_width=True)
```

- [ ] **Step 2: Manually test**

1. Log 3+ rounds with shot data
2. Navigate to Stats & Analysis
3. Confirm benchmark table shows all three columns (You, Target, Bogey, Scratch)
4. Confirm score distribution histogram renders
5. Confirm shot outcomes chart appears if shot data exists

- [ ] **Step 3: Commit**

```bash
git add pages/5_Stats.py
git commit -m "feat: add stats and analysis page with benchmarks and shot charts"
```

---

## Task 17: Profile & My Bag

**Files:**
- Create: `pages/6_Profile.py`

- [ ] **Step 1: Create pages/6_Profile.py**

```python
# pages/6_Profile.py
import streamlit as st
from src.auth import require_auth, get_current_user_id, get_supabase_client, logout
from src.db import get_user_bag, set_user_bag
from src.constants import CLUB_LIST, ALL_CLUBS

require_auth()

client = get_supabase_client()
user_id = get_current_user_id()
user = st.session_state.user

st.title("Profile & Settings")

# ── Display Name ──────────────────────────────
st.subheader("Account")
st.write(f"**Email:** {user.email}")

with st.form("display_name_form"):
    current_name = user.user_metadata.get("display_name", "") if user.user_metadata else ""
    new_name = st.text_input("Display name", value=current_name)
    if st.form_submit_button("Update Name"):
        client.auth.update_user({"data": {"display_name": new_name}})
        st.success("Name updated!")

# ── Change Password ───────────────────────────
st.subheader("Change Password")
with st.form("change_password_form"):
    new_password = st.text_input("New password", type="password")
    confirm_password = st.text_input("Confirm new password", type="password")
    if st.form_submit_button("Update Password"):
        if new_password != confirm_password:
            st.error("Passwords do not match.")
        elif len(new_password) < 6:
            st.error("Password must be at least 6 characters.")
        else:
            client.auth.update_user({"password": new_password})
            st.success("Password updated!")

st.divider()

# ── My Bag ────────────────────────────────────
st.subheader("My Bag")
st.write("Select the clubs you carry. These will appear first when tracking shots.")

current_bag = get_user_bag(client, user_id)

selected_clubs = []
for category, clubs in CLUB_LIST.items():
    st.write(f"**{category}**")
    cols = st.columns(len(clubs))
    for i, club in enumerate(clubs):
        if cols[i].checkbox(club, value=club in current_bag, key=f"bag_{club}"):
            selected_clubs.append(club)

if st.button("Save My Bag", type="primary"):
    set_user_bag(client, user_id, selected_clubs)
    st.success(f"Bag saved with {len(selected_clubs)} clubs.")
```

- [ ] **Step 2: Manually test**

1. Navigate to Profile
2. Update display name — confirm it saves
3. Select clubs for your bag
4. Click Save My Bag
5. Navigate to New Round → start a hole → open Track Shots — confirm only your bag clubs appear

- [ ] **Step 3: Commit**

```bash
git add pages/6_Profile.py
git commit -m "feat: add profile page with display name, password change, and My Bag"
```

---

## Task 18: Deployment

**Files:**
- Create: `README.md`

- [ ] **Step 1: Create README.md**

```markdown
# Lentz Caddie

Golf score and statistics tracker. Tracks rounds hole-by-hole, logs shot data,
and surfaces the top 1-2 practice focus areas based on recent performance.

## Stack
- Streamlit (Python app framework)
- Supabase (hosted Postgres + Auth)
- Plotly (charts)
- Deployed on Streamlit Community Cloud

## Local Setup

1. Clone the repo
2. Create a Supabase project at supabase.com
3. Run `db/migrations/001_initial_schema.sql` in the Supabase SQL editor
4. Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and fill in your Supabase URL and anon key
5. Install dependencies: `pip install -r requirements.txt`
6. Run: `streamlit run app.py`

## Running Tests

    pytest tests/ -v

## Deployment (Streamlit Community Cloud)

1. Push repo to GitHub (make sure `.streamlit/secrets.toml` is in `.gitignore`)
2. Go to share.streamlit.io → New App → connect your GitHub repo
3. Set main file to `app.py`
4. Under Advanced → Secrets, paste the contents of your `secrets.toml`
5. Deploy
```

- [ ] **Step 2: Push to GitHub**

Create a new repo on github.com (no README, no .gitignore — we have our own).

```bash
git remote add origin https://github.com/YOUR_USERNAME/lentz-caddie.git
git branch -M main
git push -u origin main
```

- [ ] **Step 3: Deploy to Streamlit Community Cloud**

1. Go to share.streamlit.io
2. Click "New app"
3. Select your GitHub repo, branch `main`, main file `app.py`
4. Click "Advanced settings" → "Secrets" → paste your `secrets.toml` contents
5. Click "Deploy"

Expected: App deploys and is accessible at `https://YOUR_USERNAME-lentz-caddie-app.streamlit.app`

- [ ] **Step 4: Smoke test deployed app**

1. Open the deployed URL
2. Register a new account
3. Add a course and tee
4. Log a complete round
5. Confirm dashboard shows score trend and focus areas (after 1 round, focus areas may need more data)

- [ ] **Step 5: Final commit**

```bash
git add README.md
git commit -m "docs: add README with setup and deployment instructions"
git push
```

> **Note on schema management in production:** If you need to alter the database schema after deployment, write a new migration file (e.g. `002_add_column.sql`), apply it via the Supabase dashboard SQL editor, and commit the file. Do not edit the Supabase schema directly without a corresponding migration file in the repo.

---

## Testing Summary

Run the full test suite at any time:

```bash
pytest tests/ -v
```

All tests should pass before deploying. The tests cover:
- `tests/test_constants.py` — club list completeness, benchmark structure
- `tests/test_analytics.py` — metrics computation, benchmark interpolation, focus area ranking
- `tests/test_db.py` — all db functions with mocked Supabase client
