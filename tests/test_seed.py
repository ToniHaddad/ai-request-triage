"""The three outcomes the README walks through come from the general rules, not special cases."""
import pathlib

from triage.model import (ROUTE_AUTOMATION, ROUTE_EXISTING, ROUTE_NOT_NOW, ROUTE_PILOT, STATUS_FUNDED,
                          STATUS_TRAINING, plan)
from triage.store import Store


def entries(cfg):
    return {e.req.title: e for e in plan(Store(":memory:").all(), cfg)}


def test_eight_requests(cfg):
    assert len(entries(cfg)) == 8


def test_meeting_summaries_are_existing_capability_plus_training(cfg):
    e = entries(cfg)["Meeting-summary help"]
    assert e.decision.route == ROUTE_EXISTING and e.status == STATUS_TRAINING


def test_travel_policy_is_a_custom_agent_pilot_and_funded(cfg):
    e = entries(cfg)["Travel-policy questions"]
    assert e.decision.route == ROUTE_PILOT and e.status == STATUS_FUNDED


def test_overdue_reminders_are_automation_with_no_ai(cfg):
    e = entries(cfg)["Overdue approval reminders"]
    assert e.decision.route == ROUTE_AUTOMATION and e.status == STATUS_FUNDED


def test_the_rest_follow_the_rules(cfg):
    e = entries(cfg)
    assert e["Case-note triage"].decision.rule == "R2"
    assert e["Donor report drafting from field notes"].decision.rule == "R5"
    assert e["Ask-anything intranet assistant"].decision.rule == "R1"
    assert e["Bid comparison summaries"].decision.route == ROUTE_PILOT
    assert e["Bid comparison summaries"].status != STATUS_FUNDED
    assert sum(x.decision.route == ROUTE_NOT_NOW for x in e.values()) == 3


def test_no_request_titles_appear_in_the_model_code():
    src = (pathlib.Path(__file__).parents[1] / "triage" / "model.py").read_text()
    for t in ("Travel", "Meeting", "Overdue", "Northbridge"):
        assert t not in src
