# src/constants.py

CLUB_LIST = {
    "Woods": ["Driver", "3W", "5W", "7W"],
    "Hybrids": ["2H", "3H", "4H", "5H"],
    "Irons": ["2i", "3i", "4i", "5i", "6i", "7i", "8i", "9i"],
    "Wedges": ["PW", "GW", "SW", "LW", "48°", "50°", "52°", "54°", "56°", "58°", "60°", "62°", "64°"],
    "Putter": ["Putter"],
}

ALL_CLUBS = [club for clubs in CLUB_LIST.values() for club in clubs]

# Handicap benchmarks from breakxgolf.com/golf-stats-by-handicap
# Keys are handicap index as string; "custom" handled separately
HANDICAP_BENCHMARKS = {
    "0":  {"avg_score": 74.6, "putts_per_round": 31.3, "gir_pct": 0.568, "fairways_hit_pct": 0.565},
    "5":  {"avg_score": 79.0, "putts_per_round": 32.5, "gir_pct": 0.461, "fairways_hit_pct": 0.510},
    "10": {"avg_score": 84.6, "putts_per_round": 33.9, "gir_pct": 0.373, "fairways_hit_pct": 0.493},
    "15": {"avg_score": 89.3, "putts_per_round": 34.8, "gir_pct": 0.264, "fairways_hit_pct": 0.481},
    "20": {"avg_score": 93.7, "putts_per_round": 36.1, "gir_pct": 0.224, "fairways_hit_pct": 0.428},
    "25": {"avg_score": 98.6, "putts_per_round": 37.0, "gir_pct": 0.187, "fairways_hit_pct": 0.430},
}

HANDICAP_LABELS = {
    "0":  "Scratch (0)",
    "5":  "5 Handicap",
    "10": "10 Handicap",
    "15": "15 Handicap",
    "20": "20 Handicap",
    "25": "25 Handicap",
    "custom": "Custom",
}

BENCHMARK_SOURCE = "breakxgolf.com/golf-stats-by-handicap"

# Anchor benchmarks for focus-area interpolation (scratch = hdcp 0, bogey ≈ hdcp 20)
BENCHMARKS = {
    "scratch": {
        "avg_score": 74.6,
        "putts_per_round": 31.3,
        "gir_pct": 0.568,
        "fairways_hit_pct": 0.565,
        "penalties_per_round": 0.5,
        "scoring_avg_par3": 3.1,
        "scoring_avg_par4": 4.2,
        "scoring_avg_par5": 4.8,
    },
    "bogey": {
        "avg_score": 93.7,
        "putts_per_round": 36.1,
        "gir_pct": 0.224,
        "fairways_hit_pct": 0.428,
        "penalties_per_round": 3.0,
        "scoring_avg_par3": 4.0,
        "scoring_avg_par4": 5.5,
        "scoring_avg_par5": 6.3,
    },
}

SHOT_TYPE_OPTIONS = ["tee", "fairway", "rough", "sand", "other"]
LIE_OPTIONS = ["good", "bad"]
CONTACT_OPTIONS = ["good", "chunk", "top", "fat", "thin", "toe", "heel", "other"]
MISS_DIRECTION_OPTIONS = ["left", "right"]
MISS_DISTANCE_OPTIONS = ["long", "short", "pin_high"]
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
