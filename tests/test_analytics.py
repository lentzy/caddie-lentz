# tests/test_analytics.py
import pandas as pd
import pytest
from src.analytics import compute_user_metrics, interpolate_benchmark, normalize_metric_gap


def make_hole_scores(n_rounds=5, putts_per_hole=2, gir=True, fairway="yes", penalties=0, score=4):
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
    hole_scores_df = make_hole_scores(5, fairway="yes")
    metrics = compute_user_metrics(rounds_df, hole_scores_df, pd.DataFrame())
    assert metrics["fairways_hit_pct"] == pytest.approx(1.0)


def test_compute_user_metrics_fairways_excludes_na():
    rounds_df = make_rounds(5)
    hole_scores_df = make_hole_scores(5, fairway="na")
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
