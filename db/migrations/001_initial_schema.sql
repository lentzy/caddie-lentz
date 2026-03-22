-- db/migrations/001_initial_schema.sql

-- courses: shared library, anyone can create, only creator can edit
CREATE TABLE courses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_by_user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    city TEXT NOT NULL,
    state TEXT NOT NULL,
    number_of_holes INTEGER NOT NULL DEFAULT 18,
    par_per_hole INTEGER[] NOT NULL,
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
    yardage_per_hole INTEGER[] NOT NULL,
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

-- shots: optional per hole, putts excluded
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
