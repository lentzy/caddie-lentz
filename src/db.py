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
) -> dict:
    result = client.table("rounds").insert({
        "user_id": user_id,
        "course_id": course_id,
        "tee_id": tee_id,
        "date": date,
        "holes_played": holes_played,
        "status": "in_progress",
        "notes": notes,
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
    fairway_hit: str,
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


def get_hole_score(client: Client, hole_score_id: str) -> dict | None:
    result = client.table("hole_scores").select("*").eq("id", hole_score_id).execute()
    return result.data[0] if result.data else None
