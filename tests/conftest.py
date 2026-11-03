from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

import src.app as app_module


@pytest.fixture
def activity_state(monkeypatch):
    state = deepcopy(app_module.activities)
    monkeypatch.setattr(app_module, "activities", state)
    return state


@pytest.fixture
def client(activity_state):
    with TestClient(app_module.app) as test_client:
        yield test_client