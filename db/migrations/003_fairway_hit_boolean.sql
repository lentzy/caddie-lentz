-- Migrate fairway_hit from ENUM('yes','no','na') to BOOLEAN NULL
-- TRUE = hit, FALSE = missed, NULL = n/a (par 3)

ALTER TABLE hole_scores ADD COLUMN fairway_hit_bool BOOLEAN;

UPDATE hole_scores SET fairway_hit_bool = CASE
    WHEN fairway_hit = 'yes' THEN TRUE
    WHEN fairway_hit = 'no'  THEN FALSE
    ELSE NULL
END;

ALTER TABLE hole_scores DROP COLUMN fairway_hit;
ALTER TABLE hole_scores RENAME COLUMN fairway_hit_bool TO fairway_hit;

DROP TYPE fairway_hit_type;
