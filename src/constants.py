# src/constants.py

CLUB_LIST = {
    "Woods": ["Driver", "3W", "5W", "7W"],
    "Hybrids": ["2H", "3H", "4H", "5H"],
    "Irons": ["2i", "3i", "4i", "5i", "6i", "7i", "8i", "9i"],
    "Wedges": ["PW", "GW", "SW", "LW", "48°", "50°", "52°", "54°", "56°", "58°", "60°", "62°", "64°"],
    "Putter": ["Putter"],
}

ALL_CLUBS = [club for clubs in CLUB_LIST.values() for club in clubs]

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
