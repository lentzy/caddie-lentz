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
