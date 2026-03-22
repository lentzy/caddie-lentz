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
