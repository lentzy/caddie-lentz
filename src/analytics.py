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

    # Fairways hit % (exclude 'na' holes — par 3s)
    fairway_holes = hs[hs["fairway_hit"] != "na"]
    if not fairway_holes.empty:
        metrics["fairways_hit_pct"] = float((fairway_holes["fairway_hit"] == "yes").mean())
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
