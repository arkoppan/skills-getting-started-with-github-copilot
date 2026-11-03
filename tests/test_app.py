from copy import deepcopy
from urllib.parse import quote

import pytest


def test_root_redirects_to_static_index(client):
    response = client.get("/", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/static/index.html"


def test_static_index_is_available(client):
    response = client.get("/static/index.html")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "Mergington High School" in response.text


def test_get_activities_returns_activity_details(client, activity_state):
    response = client.get("/activities")

    assert response.status_code == 200
    assert response.json() == activity_state
    assert response.json()
    for activity in response.json().values():
        assert isinstance(activity["description"], str)
        assert isinstance(activity["schedule"], str)
        assert isinstance(activity["max_participants"], int)
        assert isinstance(activity["participants"], list)


def test_signup_adds_participant_only_to_selected_activity(client, activity_state):
    activity_name = "Chess Club"
    email = "new+chess@mergington.edu"
    expected = deepcopy(activity_state)
    expected[activity_name]["participants"].append(email)

    response = client.post(
        f"/activities/{quote(activity_name, safe='')}/signup",
        params={"email": email},
    )

    assert response.status_code == 200
    assert response.json() == {"message": f"Signed up {email} for {activity_name}"}
    assert client.get("/activities").json() == expected


@pytest.mark.parametrize("method", ["POST", "DELETE"])
def test_unknown_activity_returns_404_without_changing_state(client, activity_state, method):
    expected = deepcopy(activity_state)

    response = client.request(
        method,
        "/activities/Unknown%20Club/signup",
        params={"email": "student@mergington.edu"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Activity not found"}
    assert client.get("/activities").json() == expected


def test_duplicate_signup_is_rejected_without_changing_state(client, activity_state):
    email = "new@mergington.edu"
    url = "/activities/Chess%20Club/signup"
    first_response = client.post(url, params={"email": email})
    assert first_response.status_code == 200
    expected = deepcopy(activity_state)

    response = client.post(url, params={"email": email})

    assert response.status_code == 400
    assert response.json() == {"detail": "Student already signed up for this activity"}
    assert client.get("/activities").json() == expected
    assert expected["Chess Club"]["participants"].count(email) == 1


def test_unregister_removes_only_selected_participant(client, activity_state):
    activity_name = "Chess Club"
    email = activity_state[activity_name]["participants"][0]
    expected = deepcopy(activity_state)
    expected[activity_name]["participants"].remove(email)

    response = client.delete(
        f"/activities/{quote(activity_name, safe='')}/signup",
        params={"email": email},
    )

    assert response.status_code == 200
    assert response.json() == {"message": f"Unregistered {email} from {activity_name}"}
    assert client.get("/activities").json() == expected


def test_unregister_missing_participant_returns_404_without_changing_state(client, activity_state):
    expected = deepcopy(activity_state)

    response = client.delete(
        "/activities/Chess%20Club/signup",
        params={"email": "not-registered@mergington.edu"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Student is not signed up for this activity"}
    assert client.get("/activities").json() == expected


def test_repeated_unregister_returns_404_without_changing_state(client, activity_state):
    email = activity_state["Chess Club"]["participants"][0]
    url = "/activities/Chess%20Club/signup"
    first_response = client.delete(url, params={"email": email})
    assert first_response.status_code == 200
    expected = deepcopy(activity_state)

    response = client.delete(url, params={"email": email})

    assert response.status_code == 404
    assert response.json() == {"detail": "Student is not signed up for this activity"}
    assert client.get("/activities").json() == expected


@pytest.mark.parametrize("method", ["POST", "DELETE"])
def test_missing_email_returns_422_without_changing_state(client, activity_state, method):
    expected = deepcopy(activity_state)

    response = client.request(method, "/activities/Chess%20Club/signup")

    assert response.status_code == 422
    assert any(error["loc"] == ["query", "email"] for error in response.json()["detail"])
    assert client.get("/activities").json() == expected


def test_participant_can_register_again_after_unregistering(client, activity_state):
    email = "returning+chess@mergington.edu"
    url = "/activities/Chess%20Club/signup"
    original = deepcopy(activity_state)

    assert client.post(url, params={"email": email}).status_code == 200
    assert client.delete(url, params={"email": email}).status_code == 200
    assert client.get("/activities").json() == original
    response = client.post(url, params={"email": email})

    assert response.status_code == 200
    expected = deepcopy(original)
    expected["Chess Club"]["participants"].append(email)
    assert client.get("/activities").json() == expected