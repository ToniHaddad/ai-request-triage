import pytest
from fastapi.testclient import TestClient

from triage.app import create_app
from triage.store import Store


@pytest.fixture()
def client(cfg):
    return TestClient(create_app(Store(":memory:"), cfg))


def test_page_is_served(client):
    r = client.get("/")
    assert r.status_code == 200 and "AI request triage" in r.text


def test_roadmap_has_eight_items(client):
    d = client.get("/api/roadmap").json()
    assert len(d["items"]) == 8 and d["slots"] == 2
    assert [i["status"] for i in d["items"]].count("funded") == 2


def test_slots_query(client):
    d = client.get("/api/roadmap?slots=3").json()
    assert [i["status"] for i in d["items"]].count("funded") == 3


def test_memo_has_the_computed_sections(client):
    m = client.get("/api/requests/2/memo").json()
    assert m["entry"]["route"] == "agent_pilot"
    assert m["drivers"] and len(m["change"]) == 2 and "percent of 1000 runs" in m["stability_text"]


def test_memo_404(client):
    assert client.get("/api/requests/99/memo").status_code == 404


def test_intake_adds_and_reranks(client):
    body = dict(team="Test", title="New thing", per_week=5, people=50, minutes=40, owner="Ana",
                data_class="internal", success_text="down 30 percent", success_measurable=True,
                existing_tool="no", task_kind="language", consequence="medium", systems=2)
    r = client.post("/api/requests", json=body)
    assert r.status_code == 201
    assert len(client.get("/api/roadmap").json()["items"]) == 9
    assert client.delete(f"/api/requests/{r.json()['id']}").status_code == 200


def test_intake_rejects_bad_input(client):
    assert client.post("/api/requests", json={"team": "x"}).status_code == 422


def test_config_endpoint_shows_weights_and_rules(client):
    d = client.get("/api/config").json()
    assert d["config"]["weights"]["value"] == 0.45 and len(d["rules"]) == 5
