-- Migration 005: Add miss_distance to shots
CREATE TYPE miss_distance_enum AS ENUM ('long', 'short', 'pin_high');

ALTER TABLE shots ADD COLUMN miss_distance miss_distance_enum;
