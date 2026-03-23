# src/analytics.py
import pandas as pd
from src.constants import BENCHMARKS

# Metrics where LOWER value is better
LOWER_IS_BETTER = {
    "putts_per_round", "penalties_per_round",
    "scoring_avg_par3", "scoring_avg_par4", "scoring_avg_par5"
}
# Metrics where HIGHER value is better
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
    """Compute average metrics across the provided rounds. Returns {} if no data."""
    if rounds_df.empty or hole_scores_df.empty:
        return {}

    round_ids = rounds_df["id"].tolist()
    hs = hole_scores_df[hole_scores_df["round_id"].isin(round_ids)].copy()

    if hs.empty:
        return {}

    metrics = {}

    # Putts per round
    metrics["putts_per_round"] = hs.groupby("round_id")["putts"].sum().mean()

    # GIR %
    metrics["gir_pct"] = float(hs["green_in_regulation"].mean())

    # Fairways hit % (exclude NULL holes — par 3s)
    fairway_holes = hs[hs["fairway_hit"].notna()]
    if not fairway_holes.empty:
        metrics["fairways_hit_pct"] = float(fairway_holes["fairway_hit"].mean())
    else:
        metrics["fairways_hit_pct"] = None

    # Penalties per round
    metrics["penalties_per_round"] = hs.groupby("round_id")["penalties"].sum().mean()

    # Avg score by par type (requires 'par' column joined from course data)
    if "par" in hs.columns:
        for par in [3, 4, 5]:
            par_holes = hs[hs["par"] == par]
            if not par_holes.empty:
                metrics[f"scoring_avg_par{par}"] = float(par_holes["score"].mean())

    # Recent avg score for benchmark interpolation
    if "total_score" in rounds_df.columns:
        metrics["avg_score"] = float(rounds_df["total_score"].mean())

    return metrics


def interpolate_benchmark(avg_score: float) -> dict:
    """
    Linearly interpolate between scratch and bogey benchmarks based on avg_score.
    Clamps to [72, 95] range — no extrapolation beyond anchors.
    """
    scratch = BENCHMARKS["scratch"]
    bogey = BENCHMARKS["bogey"]
    scratch_score = scratch["avg_score"]  # 72
    bogey_score = bogey["avg_score"]      # 95

    clamped = max(scratch_score, min(bogey_score, avg_score))
    t = (clamped - scratch_score) / (bogey_score - scratch_score)

    target = {}
    for metric in scratch:
        if metric == "avg_score":
            continue
        target[metric] = scratch[metric] + t * (bogey[metric] - scratch[metric])
    return target


def normalize_metric_gap(metric: str, user_value: float, target_value: float) -> float:
    """
    Return a positive float when user is WORSE than target, normalized by scratch-to-bogey range.
    Returns 0 when user matches target, negative when user is better.
    """
    scratch_val = BENCHMARKS["scratch"].get(metric, 0)
    bogey_val = BENCHMARKS["bogey"].get(metric, 1)
    full_range = abs(bogey_val - scratch_val) or 1.0

    if metric in LOWER_IS_BETTER:
        raw_gap = user_value - target_value
    else:
        raw_gap = target_value - user_value

    return raw_gap / full_range


def rank_focus_areas(
    user_metrics: dict,
    n: int = 2,
    recent_metrics: dict = None,
    prior_metrics: dict = None,
) -> list[dict]:
    """
    Rank metrics by gap vs interpolated personal benchmark.
    Returns top n focus areas sorted by gap_score descending.
    gap_score = 0.7 * absolute_gap + 0.3 * trend_gap (recent 5 vs prior 5 rounds).
    Trend component is omitted when recent_metrics/prior_metrics are not provided.
    """
    avg_score = user_metrics.get("avg_score", 90)
    target = interpolate_benchmark(avg_score)

    ranked = []
    for metric, target_value in target.items():
        user_value = user_metrics.get(metric)
        if user_value is None:
            continue
        abs_gap = normalize_metric_gap(metric, user_value, target_value)

        trend_gap = 0.0
        if recent_metrics and prior_metrics:
            recent_val = recent_metrics.get(metric)
            prior_val = prior_metrics.get(metric)
            if recent_val is not None and prior_val is not None:
                # Positive = getting worse recently
                trend_gap = normalize_metric_gap(metric, recent_val, prior_val)

        gap_score = 0.7 * abs_gap + 0.3 * trend_gap
        if gap_score <= 0:
            continue
        ranked.append({
            "metric": metric,
            "display_name": METRIC_DISPLAY_NAMES.get(metric, metric),
            "user_value": user_value,
            "target_value": target_value,
            "gap_score": gap_score,
        })

    ranked.sort(key=lambda x: x["gap_score"], reverse=True)
    return ranked[:n]


def get_shot_pattern_insight(
    metric: str,
    shots_df: pd.DataFrame,
    hole_scores_df: pd.DataFrame,
) -> str | None:
    """
    Generate a plain-English insight for a focus area using shot data.
    Returns None if not enough data or no clear pattern.
    Minimum 5 relevant shots required before generating an insight.
    """
    if shots_df.empty:
        return None

    MIN_SHOTS = 5

    if metric == "fairways_hit_pct":
        tee_shots = shots_df[shots_df.get("shot_type", pd.Series(dtype=str)) == "tee"] if "shot_type" in shots_df.columns else shots_df
        missed = tee_shots[tee_shots["miss_direction"].notna()] if "miss_direction" in tee_shots.columns else pd.DataFrame()
        if len(missed) < MIN_SHOTS:
            return None
        left_pct = (missed["miss_direction"] == "left").mean()
        right_pct = (missed["miss_direction"] == "right").mean()
        dominant = "left" if left_pct >= right_pct else "right"
        dominant_pct = max(left_pct, right_pct)
        if dominant_pct >= 0.60:
            pattern = "pull/hook" if dominant == "left" else "push/slice"
            return f"{dominant_pct:.0%} of missed fairways go {dominant} — suggests a consistent {pattern} pattern"
        return None

    elif metric == "gir_pct":
        if "miss_direction" not in shots_df.columns:
            return None
        missed_approach = shots_df[shots_df["miss_direction"].notna()]
        if len(missed_approach) < MIN_SHOTS:
            return None
        left_pct = (missed_approach["miss_direction"] == "left").mean()
        right_pct = (missed_approach["miss_direction"] == "right").mean()
        dominant = "left" if left_pct >= right_pct else "right"
        dominant_pct = max(left_pct, right_pct)
        if dominant_pct >= 0.55:
            return f"{dominant_pct:.0%} of approach misses go {dominant} — consistent ball flight issue on approach shots"
        return None

    elif metric == "putts_per_round":
        return "Consider tracking individual putts to identify whether the issue is distance control or short putting"

    return None


def build_focus_area_cards(
    user_metrics: dict,
    shots_df: pd.DataFrame,
    hole_scores_df: pd.DataFrame,
    n_shot_rounds: int = 0,
    recent_metrics: dict = None,
    prior_metrics: dict = None,
) -> list[dict]:
    """
    Return top 2 focus area dicts ready to render in the UI.
    Each dict has: metric, display_name, user_value, target_value, gap_score, insight.
    insight is None if not enough shot data (< 3 rounds with shots).
    recent_metrics / prior_metrics enable 70/30 trend weighting in ranking.
    """
    MIN_SHOT_ROUNDS = 3
    areas = rank_focus_areas(user_metrics, n=2, recent_metrics=recent_metrics, prior_metrics=prior_metrics)

    for area in areas:
        if n_shot_rounds >= MIN_SHOT_ROUNDS:
            area["insight"] = get_shot_pattern_insight(
                area["metric"], shots_df, hole_scores_df
            )
        else:
            area["insight"] = None

    return areas
