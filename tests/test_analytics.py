# tests/test_analytics.py
import pandas as pd
import pytest
from src.analytics import compute_user_metrics, interpolate_benchmark, normalize_metric_gap


def make_hole_scores(n_rounds=5, putts_per_hole=2, gir=True, fairway=True, penalties=0, score=4):
    rows = []
    for r in range(n_rounds):
        for h in range(1, 19):
            rows.append({
                "round_id": f"r{r}",
                "hole_number": h,
                "score": score,
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


def test_compute_user_metrics_gir_pct_all_true():
    rounds_df = make_rounds(5)
    hole_scores_df = make_hole_scores(5, gir=True)
    metrics = compute_user_metrics(rounds_df, hole_scores_df, pd.DataFrame())
    assert metrics["gir_pct"] == pytest.approx(1.0)


def test_compute_user_metrics_gir_pct_all_false():
    rounds_df = make_rounds(5)
    hole_scores_df = make_hole_scores(5, gir=False)
    metrics = compute_user_metrics(rounds_df, hole_scores_df, pd.DataFrame())
    assert metrics["gir_pct"] == pytest.approx(0.0)


def test_compute_user_metrics_fairways_hit_pct():
    rounds_df = make_rounds(5)
    hole_scores_df = make_hole_scores(5, fairway=True)
    metrics = compute_user_metrics(rounds_df, hole_scores_df, pd.DataFrame())
    assert metrics["fairways_hit_pct"] == pytest.approx(1.0)


def test_compute_user_metrics_fairways_excludes_na():
    rounds_df = make_rounds(5)
    hole_scores_df = make_hole_scores(5, fairway=None)
    metrics = compute_user_metrics(rounds_df, hole_scores_df, pd.DataFrame())
    assert metrics["fairways_hit_pct"] is None


def test_compute_user_metrics_avg_score():
    rounds_df = make_rounds(5, avg_score=90)
    hole_scores_df = make_hole_scores(5)
    metrics = compute_user_metrics(rounds_df, hole_scores_df, pd.DataFrame())
    assert metrics["avg_score"] == pytest.approx(90.0)


def test_compute_user_metrics_empty_returns_empty():
    metrics = compute_user_metrics(pd.DataFrame(), pd.DataFrame(), pd.DataFrame())
    assert metrics == {}


def test_interpolate_benchmark_at_scratch():
    target = interpolate_benchmark(avg_score=72)
    assert target["putts_per_round"] == pytest.approx(29.0)
    assert target["gir_pct"] == pytest.approx(0.67)


def test_interpolate_benchmark_at_bogey():
    target = interpolate_benchmark(avg_score=95)
    assert target["putts_per_round"] == pytest.approx(36.0)


def test_interpolate_benchmark_midpoint():
    target = interpolate_benchmark(avg_score=83.5)
    assert target["putts_per_round"] == pytest.approx((29 + 36) / 2, rel=0.05)


def test_interpolate_benchmark_clamps_below_scratch():
    target = interpolate_benchmark(avg_score=60)
    assert target["putts_per_round"] == pytest.approx(29.0)


def test_interpolate_benchmark_clamps_above_bogey():
    target = interpolate_benchmark(avg_score=120)
    assert target["putts_per_round"] == pytest.approx(36.0)


def test_normalize_metric_gap_higher_is_worse():
    # putts: user has 38, target 33 → positive gap (user is worse)
    gap = normalize_metric_gap("putts_per_round", user_value=38, target_value=33)
    assert gap > 0


def test_normalize_metric_gap_higher_is_better():
    # gir_pct: user has 0.20, target 0.35 → positive gap (user is worse)
    gap = normalize_metric_gap("gir_pct", user_value=0.20, target_value=0.35)
    assert gap > 0


def test_normalize_metric_gap_user_at_target():
    gap = normalize_metric_gap("putts_per_round", user_value=33, target_value=33)
    assert gap == pytest.approx(0.0)


from src.analytics import rank_focus_areas, get_shot_pattern_insight, build_focus_area_cards


def test_rank_focus_areas_returns_top_2():
    user_metrics = {
        "avg_score": 95,
        "putts_per_round": 38,      # worse than bogey target
        "gir_pct": 0.20,            # worse than bogey target
        "fairways_hit_pct": 0.55,   # close to bogey target
        "penalties_per_round": 2.0,
    }
    focus_areas = rank_focus_areas(user_metrics, n=2)
    assert len(focus_areas) == 2
    assert "metric" in focus_areas[0]
    assert "gap_score" in focus_areas[0]
    assert "display_name" in focus_areas[0]
    assert "user_value" in focus_areas[0]
    assert "target_value" in focus_areas[0]
    # highest gap first
    assert focus_areas[0]["gap_score"] >= focus_areas[1]["gap_score"]


def test_rank_focus_areas_excludes_none_metrics():
    user_metrics = {
        "avg_score": 90,
        "putts_per_round": 34,
        "gir_pct": None,  # not enough data
        "fairways_hit_pct": 0.45,
    }
    focus_areas = rank_focus_areas(user_metrics, n=2)
    metrics_returned = [fa["metric"] for fa in focus_areas]
    assert "gir_pct" not in metrics_returned


def test_rank_focus_areas_excludes_metrics_at_or_better_than_target():
    # User is AT the scratch benchmark for putts — should not appear as a focus area
    user_metrics = {
        "avg_score": 72,
        "putts_per_round": 29,      # exactly at scratch target
        "gir_pct": 0.20,            # worse than target
        "fairways_hit_pct": 0.30,   # worse than target
    }
    focus_areas = rank_focus_areas(user_metrics, n=2)
    metrics_returned = [fa["metric"] for fa in focus_areas]
    assert "putts_per_round" not in metrics_returned


def test_rank_focus_areas_fewer_than_n_when_all_at_target():
    user_metrics = {
        "avg_score": 95,
        "putts_per_round": 36,      # exactly at bogey target
        "gir_pct": 0.25,            # exactly at bogey target
    }
    focus_areas = rank_focus_areas(user_metrics, n=2)
    # Both at target — gap_score <= 0 — should return empty list
    assert len(focus_areas) == 0


def test_shot_pattern_insight_miss_direction_fairways():
    shots_df = pd.DataFrame([
        {"shot_type": "tee", "miss_direction": "left"},
        {"shot_type": "tee", "miss_direction": "left"},
        {"shot_type": "tee", "miss_direction": "left"},
        {"shot_type": "tee", "miss_direction": "left"},
        {"shot_type": "tee", "miss_direction": "right"},
    ])
    insight = get_shot_pattern_insight("fairways_hit_pct", shots_df, pd.DataFrame())
    assert insight is not None
    assert "left" in insight.lower()
    assert "80%" in insight or "4 of 5" in insight or "left" in insight


def test_shot_pattern_insight_returns_none_with_insufficient_data():
    shots_df = pd.DataFrame([
        {"shot_type": "tee", "miss_direction": "left"},
        {"shot_type": "tee", "miss_direction": "right"},
    ])  # only 2 shots — below minimum of 5
    insight = get_shot_pattern_insight("fairways_hit_pct", shots_df, pd.DataFrame())
    assert insight is None


def test_shot_pattern_insight_returns_none_for_unknown_metric():
    shots_df = pd.DataFrame([{"shot_type": "tee", "miss_direction": "left"}] * 10)
    insight = get_shot_pattern_insight("unknown_metric", shots_df, pd.DataFrame())
    assert insight is None


def test_build_focus_area_cards_adds_insight_when_enough_shot_rounds():
    user_metrics = {
        "avg_score": 90,
        "putts_per_round": 38,
        "gir_pct": 0.20,
        "fairways_hit_pct": 0.30,
        "penalties_per_round": 2.0,
    }
    shots_df = pd.DataFrame(
        [{"shot_type": "tee", "miss_direction": "left"}] * 8 +
        [{"shot_type": "tee", "miss_direction": "right"}] * 2
    )
    cards = build_focus_area_cards(user_metrics, shots_df, pd.DataFrame(), n_shot_rounds=3)
    assert len(cards) == 2
    # All cards have an "insight" key (may be None for some metrics)
    for card in cards:
        assert "insight" in card


def test_build_focus_area_cards_no_insight_below_threshold():
    user_metrics = {
        "avg_score": 90,
        "putts_per_round": 38,
        "gir_pct": 0.20,
        "fairways_hit_pct": 0.30,
    }
    cards = build_focus_area_cards(user_metrics, pd.DataFrame(), pd.DataFrame(), n_shot_rounds=2)
    for card in cards:
        assert card["insight"] is None


def test_rank_focus_areas_trend_raises_ranking():
    """A metric that is getting worse recently should outscore one with same absolute gap but stable trend."""
    user_metrics = {"avg_score": 90, "putts_per_round": 35, "gir_pct": 0.28}
    # Both metrics have similar absolute gaps vs target.
    # Putting is getting worse recently; GIR is stable.
    recent_metrics = {"avg_score": 90, "putts_per_round": 38, "gir_pct": 0.28}
    prior_metrics = {"avg_score": 90, "putts_per_round": 33, "gir_pct": 0.28}
    areas = rank_focus_areas(user_metrics, n=2, recent_metrics=recent_metrics, prior_metrics=prior_metrics)
    metric_names = [a["metric"] for a in areas]
    # Putting should rank first because trend is worsening
    assert metric_names[0] == "putts_per_round"


def test_rank_focus_areas_without_trend_uses_absolute_gap_only():
    """Without recent/prior metrics, gap_score is based purely on absolute gap."""
    user_metrics = {"avg_score": 90, "putts_per_round": 38, "gir_pct": 0.20}
    areas_no_trend = rank_focus_areas(user_metrics, n=2)
    areas_with_stable_trend = rank_focus_areas(
        user_metrics, n=2,
        recent_metrics={"putts_per_round": 38, "gir_pct": 0.20},
        prior_metrics={"putts_per_round": 38, "gir_pct": 0.20},
    )
    # Order should be the same — stable trend doesn't change ranking
    assert [a["metric"] for a in areas_no_trend] == [a["metric"] for a in areas_with_stable_trend]