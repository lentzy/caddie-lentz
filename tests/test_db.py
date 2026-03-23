# tests/test_db.py
from unittest.mock import MagicMock
import pytest
from src.db import get_courses, create_course, get_course, update_course, delete_course, get_tees, get_tee, create_tee, update_tee, delete_tee


def make_mock_client():
    return MagicMock()


# ── COURSES ──────────────────────────────────

def test_get_courses_returns_list():
    client = make_mock_client()
    client.table.return_value.select.return_value.order.return_value.execute.return_value.data = [
        {"id": "abc", "name": "Augusta National", "city": "Augusta", "state": "GA"}
    ]
    result = get_courses(client)
    assert len(result) == 1
    assert result[0]["name"] == "Augusta National"


def test_get_courses_filters_by_search():
    client = make_mock_client()
    client.table.return_value.select.return_value.ilike.return_value.order.return_value.execute.return_value.data = [
        {"id": "abc", "name": "Augusta National"}
    ]
    result = get_courses(client, search="Augusta")
    assert len(result) == 1


def test_create_course_inserts_correctly():
    client = make_mock_client()
    client.table.return_value.insert.return_value.execute.return_value.data = [
        {"id": "new-id", "name": "Pebble Beach"}
    ]
    result = create_course(
        client,
        user_id="user-1",
        name="Pebble Beach",
        city="Pebble Beach",
        state="CA",
        par_per_hole=[4,5,4,4,3,5,3,4,4,4,4,3,4,5,4,4,3,5],
    )
    assert result["name"] == "Pebble Beach"
    client.table.return_value.insert.assert_called_once()


def test_create_course_rejects_wrong_par_length():
    client = make_mock_client()
    with pytest.raises(ValueError, match="par_per_hole must have exactly 18 values"):
        create_course(client, "u1", "Short Course", "City", "ST", [4, 4, 4])


def test_get_tees_for_course():
    client = make_mock_client()
    client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = [
        {"id": "t1", "tee_name": "Blue", "rating": 74.2, "slope": 138}
    ]
    result = get_tees(client, course_id="course-1")
    assert len(result) == 1
    assert result[0]["tee_name"] == "Blue"


def test_create_tee_rejects_wrong_yardage_length():
    client = make_mock_client()
    with pytest.raises(ValueError, match="yardage_per_hole must have exactly 18 values"):
        create_tee(client, "u1", "c1", "Blue", 72.0, 113, [400] * 9)


from src.db import (
    create_round, get_round, get_rounds, get_in_progress_round,
    complete_round, upsert_hole_score, get_hole_scores, get_hole_score
)


def test_create_round():
    client = make_mock_client()
    client.table.return_value.insert.return_value.execute.return_value.data = [
        {"id": "r1", "status": "in_progress", "user_id": "u1"}
    ]
    result = create_round(client, user_id="u1", course_id="c1", tee_id="t1",
                          date="2026-03-22", holes_played="full")
    assert result["status"] == "in_progress"


def test_get_in_progress_round_returns_none_when_absent():
    client = make_mock_client()
    client.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
    result = get_in_progress_round(client, user_id="u1")
    assert result is None


def test_get_in_progress_round_returns_round_when_present():
    client = make_mock_client()
    client.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
        {"id": "r1", "status": "in_progress"}
    ]
    result = get_in_progress_round(client, user_id="u1")
    assert result["id"] == "r1"


def test_upsert_hole_score():
    client = make_mock_client()
    client.table.return_value.upsert.return_value.execute.return_value.data = [
        {"id": "hs1", "hole_number": 1, "score": 4}
    ]
    result = upsert_hole_score(client, round_id="r1", hole_number=1,
                               score=4, putts=2, fairway_hit=True,
                               green_in_regulation=True, penalties=0)
    assert result["hole_number"] == 1
    assert result["score"] == 4


def test_get_hole_scores_returns_list():
    client = make_mock_client()
    client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = [
        {"id": "hs1", "hole_number": 1, "score": 4},
        {"id": "hs2", "hole_number": 2, "score": 5},
    ]
    result = get_hole_scores(client, round_id="r1")
    assert len(result) == 2


# ─────────────────────────────────────────────
# SHOTS
# ─────────────────────────────────────────────

from src.db import create_shot, get_shots, delete_shots_for_hole, get_user_bag, set_user_bag


def test_create_shot():
    client = make_mock_client()
    client.table.return_value.insert.return_value.execute.return_value.data = [
        {"id": "s1", "shot_number": 1, "club": "7i", "outcome": "green"}
    ]
    result = create_shot(client, hole_score_id="hs1", shot_number=1,
                         distance_to_hole=150, club="7i", shot_type="fairway",
                         lie="good", contact=["good"], miss_direction=None,
                         outcome="green", penalty_reason=None, distance_hit=145)
    assert result["club"] == "7i"


def test_get_user_bag():
    client = make_mock_client()
    client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = [
        {"club": "Driver"}, {"club": "7i"}, {"club": "PW"}
    ]
    result = get_user_bag(client, user_id="u1")
    assert "Driver" in result
    assert len(result) == 3


def test_set_user_bag_replaces_existing():
    client = make_mock_client()
    client.table.return_value.delete.return_value.eq.return_value.execute.return_value.data = []
    client.table.return_value.insert.return_value.execute.return_value.data = [
        {"club": "Driver"}, {"club": "7i"}
    ]
    set_user_bag(client, user_id="u1", clubs=["Driver", "7i"])
    client.table.return_value.delete.assert_called()
    client.table.return_value.insert.assert_called()
