-- Migration 006: user settings for stat targets
CREATE TABLE user_settings (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    target_handicap TEXT NOT NULL DEFAULT '20',  -- "0","5","10","15","20","25", or "custom"
    custom_putts_per_round NUMERIC(4,1),
    custom_gir_pct NUMERIC(4,3),
    custom_fairways_hit_pct NUMERIC(4,3),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE user_settings ENABLE ROW LEVEL SECURITY;
CREATE POLICY "user_settings_owner" ON user_settings FOR ALL TO authenticated
    USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());
