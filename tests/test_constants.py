from src.constants import CLUB_LIST, ALL_CLUBS, BENCHMARKS, CONTACT_OPTIONS, OUTCOME_OPTIONS

def test_club_list_has_all_categories():
    assert "Woods" in CLUB_LIST
    assert "Hybrids" in CLUB_LIST
    assert "Irons" in CLUB_LIST
    assert "Wedges" in CLUB_LIST
    assert "Putter" in CLUB_LIST

def test_club_list_key_clubs_present():
    assert "Driver" in ALL_CLUBS
    assert "7i" in ALL_CLUBS
    assert "SW" in ALL_CLUBS
    assert "58°" in ALL_CLUBS
    assert "Putter" in ALL_CLUBS

def test_club_list_no_duplicates():
    assert len(ALL_CLUBS) == len(set(ALL_CLUBS))

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
    assert BENCHMARKS["scratch"]["avg_score"] < BENCHMARKS["bogey"]["avg_score"]

def test_contact_options_complete():
    assert "good" in CONTACT_OPTIONS
    assert "chunk" in CONTACT_OPTIONS
    assert "toe" in CONTACT_OPTIONS
    assert "heel" in CONTACT_OPTIONS

def test_outcome_options_complete():
    assert "fairway" in OUTCOME_OPTIONS
    assert "green" in OUTCOME_OPTIONS
    assert "penalty" in OUTCOME_OPTIONS
