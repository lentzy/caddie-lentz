# src/db.py
from supabase import Client


# ─────────────────────────────────────────────
# COURSES
# ─────────────────────────────────────────────

def get_courses(client: Client, search: str = None) -> list[dict]:
    """Return all courses sorted alphabetically, optionally filtered by name."""
    query = client.table("courses").select("*")
    if search:
        query = query.ilike("name", f"%{search}%")
    return query.order("name").execute().data


def get_courses_by_ids(client: Client, course_ids: list[str]) -> list[dict]:
    """Fetch multiple courses by ID in a single query."""
    if not course_ids:
        return []
    return client.table("courses").select("*").in_("id", course_ids).execute().data


def get_course(client: Client, course_id: str) -> dict | None:
    result = client.table("courses").select("*").eq("id", course_id).execute()
    return result.data[0] if result.data else None


def create_course(
    client: Client,
    user_id: str,
    name: str,
    city: str,
    state: str,
    par_per_hole: list[int],
    website: str | None = None,
) -> dict:
    if len(par_per_hole) != 18:
        raise ValueError("par_per_hole must have exactly 18 values")
    result = client.table("courses").insert({
        "created_by_user_id": user_id,
        "name": name,
        "city": city,
        "state": state,
        "number_of_holes": 18,
        "par_per_hole": par_per_hole,
        "website": website or None,
    }).execute()
    return result.data[0]


def update_course(client: Client, course_id: str, **kwargs) -> dict:
    result = client.table("courses").update(kwargs).eq("id", course_id).execute()
    return result.data[0]


def delete_course(client: Client, course_id: str):
    client.table("courses").delete().eq("id", course_id).execute()


# ─────────────────────────────────────────────
# TEES
# ─────────────────────────────────────────────

def get_tees(client: Client, course_id: str) -> list[dict]:
    return client.table("tees").select("*").eq("course_id", course_id).order("tee_name").execute().data


def get_tee(client: Client, tee_id: str) -> dict | None:
    result = client.table("tees").select("*").eq("id", tee_id).execute()
    return result.data[0] if result.data else None


def create_tee(
    client: Client,
    user_id: str,
    course_id: str,
    tee_name: str,
    rating: float,
    slope: int,
    yardage_per_hole: list[int],
) -> dict:
    if len(yardage_per_hole) != 18:
        raise ValueError("yardage_per_hole must have exactly 18 values")
    result = client.table("tees").insert({
        "created_by_user_id": user_id,
        "course_id": course_id,
        "tee_name": tee_name,
        "rating": rating,
        "slope": slope,
        "yardage_per_hole": yardage_per_hole,
    }).execute()
    return result.data[0]


def update_tee(client: Client, tee_id: str, **kwargs) -> dict:
    result = client.table("tees").update(kwargs).eq("id", tee_id).execute()
    return result.data[0]


def delete_tee(client: Client, tee_id: str):
    client.table("tees").delete().eq("id", tee_id).execute()


# ─────────────────────────────────────────────
# ROUNDS
# ─────────────────────────────────────────────

def create_round(
    client: Client,
    user_id: str,
    course_id: str,
    tee_id: str,
    date: str,
    holes_played: str = "full",
    notes: str = None,
    name: str = None,
) -> dict:
    if not name:
        existing = client.table("rounds").select("id", count="exact").eq("user_id", user_id).eq("date", date).execute()
        count = existing.count or 0
        name = date if count == 0 else f"{date} #{count + 1}"
    result = client.table("rounds").insert({
        "user_id": user_id,
        "course_id": course_id,
        "tee_id": tee_id,
        "date": date,
        "holes_played": holes_played,
        "status": "in_progress",
        "notes": notes,
        "name": name,
    }).execute()
    return result.data[0]


def get_round(client: Client, round_id: str) -> dict | None:
    result = client.table("rounds").select("*, tees(rating, slope)").eq("id", round_id).execute()
    return result.data[0] if result.data else None


def get_rounds(client: Client, user_id: str, status: str = None, limit: int = 20) -> list[dict]:
    query = client.table("rounds").select("*, courses(name), tees(tee_name)").eq("user_id", user_id)
    if status:
        query = query.eq("status", status)
    return query.order("date", desc=True).limit(limit).execute().data


def get_in_progress_round(client: Client, user_id: str) -> dict | None:
    result = (
        client.table("rounds")
        .select("*, courses(name), tees(tee_name)")
        .eq("user_id", user_id)
        .eq("status", "in_progress")
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def complete_round(client: Client, round_id: str) -> dict:
    """Compute total_score and differential, mark round complete."""
    round_data = get_round(client, round_id)
    hole_scores = get_hole_scores(client, round_id)
    total_score = sum(h["score"] for h in hole_scores)

    differential = None
    if round_data and round_data.get("holes_played") == "full" and round_data.get("tees"):
        rating = round_data["tees"]["rating"]
        slope = round_data["tees"]["slope"]
        differential = round((113 / slope) * (total_score - rating), 2)

    result = client.table("rounds").update({
        "status": "complete",
        "total_score": total_score,
        "differential": differential,
    }).eq("id", round_id).execute()
    return result.data[0]


def update_round(client: Client, round_id: str, **kwargs) -> dict:
    result = client.table("rounds").update(kwargs).eq("id", round_id).execute()
    return result.data[0]


def delete_round(client: Client, round_id: str):
    client.table("rounds").delete().eq("id", round_id).execute()


# ─────────────────────────────────────────────
# HOLE SCORES
# ─────────────────────────────────────────────

def upsert_hole_score(
    client: Client,
    round_id: str,
    hole_number: int,
    score: int,
    putts: int,
    fairway_hit: bool | None,
    green_in_regulation: bool,
    penalties: int,
) -> dict:
    result = client.table("hole_scores").upsert({
        "round_id": round_id,
        "hole_number": hole_number,
        "score": score,
        "putts": putts,
        "fairway_hit": fairway_hit,
        "green_in_regulation": green_in_regulation,
        "penalties": penalties,
    }, on_conflict="round_id,hole_number").execute()
    return result.data[0]


def get_hole_scores(client: Client, round_id: str) -> list[dict]:
    return (
        client.table("hole_scores")
        .select("*")
        .eq("round_id", round_id)
        .order("hole_number")
        .execute()
        .data
    )


def get_hole_scores_for_rounds(client: Client, round_ids: list[str]) -> list[dict]:
    """Fetch all hole scores for multiple rounds in a single query."""
    if not round_ids:
        return []
    return (
        client.table("hole_scores")
        .select("*")
        .in_("round_id", round_ids)
        .order("hole_number")
        .execute()
        .data
    )


def get_hole_score(client: Client, hole_score_id: str) -> dict | None:
    result = client.table("hole_scores").select("*").eq("id", hole_score_id).execute()
    return result.data[0] if result.data else None


# ─────────────────────────────────────────────
# SHOTS
# ─────────────────────────────────────────────

def create_shot(
    client: Client,
    hole_score_id: str,
    shot_number: int,
    distance_to_hole: int | None,
    club: str,
    shot_type: str,
    lie: str,
    contact: list[str],
    miss_direction: str | None,
    outcome: str,
    penalty_reason: str | None,
    distance_hit: int | None = None,
) -> dict:
    result = client.table("shots").insert({
        "hole_score_id": hole_score_id,
        "shot_number": shot_number,
        "distance_to_hole": distance_to_hole,
        "club": club,
        "shot_type": shot_type,
        "lie": lie,
        "contact": contact,
        "miss_direction": miss_direction,
        "outcome": outcome,
        "penalty_reason": penalty_reason,
        "distance_hit": distance_hit,
    }).execute()
    return result.data[0]


def get_shots(client: Client, hole_score_id: str) -> list[dict]:
    return (
        client.table("shots")
        .select("*")
        .eq("hole_score_id", hole_score_id)
        .order("shot_number")
        .execute()
        .data
    )


def get_shots_for_hole_scores(client: Client, hole_score_ids: list[str]) -> list[dict]:
    """Fetch all shots for multiple hole scores in a single query."""
    if not hole_score_ids:
        return []
    return (
        client.table("shots")
        .select("*")
        .in_("hole_score_id", hole_score_ids)
        .order("shot_number")
        .execute()
        .data
    )


def update_shot(client: Client, shot_id: str, **kwargs) -> dict:
    result = client.table("shots").update(kwargs).eq("id", shot_id).execute()
    return result.data[0]


def delete_shot(client: Client, shot_id: str):
    client.table("shots").delete().eq("id", shot_id).execute()


def delete_shots_for_hole(client: Client, hole_score_id: str):
    client.table("shots").delete().eq("hole_score_id", hole_score_id).execute()


# ─────────────────────────────────────────────
# USER BAG
# ─────────────────────────────────────────────

def get_user_bag(client: Client, user_id: str) -> list[str]:
    """Return list of club names in the user's bag."""
    result = (
        client.table("user_bag")
        .select("club")
        .eq("user_id", user_id)
        .order("club")
        .execute()
    )
    return [row["club"] for row in result.data]


def set_user_bag(client: Client, user_id: str, clubs: list[str]):
    """Replace the user's entire bag with the given club list."""
    client.table("user_bag").delete().eq("user_id", user_id).execute()
    if clubs:
        rows = [{"user_id": user_id, "club": club} for club in clubs]
        client.table("user_bag").insert(rows).execute()
