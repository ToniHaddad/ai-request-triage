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
    e = entries(cfg)["Summaries of long meetings"]
    assert e.decision.route == ROUTE_EXISTING and e.status == STATUS_TRAINING


def test_procedure_questions_are_a_custom_agent_pilot_and_funded(cfg):
    e = entries(cfg)["Which procedure applies?"]
    assert e.decision.route == ROUTE_PILOT and e.status == STATUS_FUNDED


def test_rental_reminders_are_automation_with_no_ai(cfg):
    e = entries(cfg)["Rental contract end reminders"]
    assert e.decision.route == ROUTE_AUTOMATION and e.decision.rule == "R4"


def test_purchase_order_rows_are_automation_and_funded(cfg):
    e = entries(cfg)["Purchase order rows into the stock system"]
    assert e.decision.route == ROUTE_AUTOMATION and e.status == STATUS_FUNDED


def test_the_rest_follow_the_rules(cfg):
    e = entries(cfg)
    assert e["Protection case-note triage"].decision.rule == "R2"
    ask = e["Ask-anything intranet assistant"].decision
    assert (ask.route, ask.rule) == (ROUTE_NOT_NOW, "R5") and "owner" in ask.reason and "measurable" in ask.reason
    assert e["Donor report narrative from stock figures"].decision.route == ROUTE_PILOT
    assert e["Operations room chat into a situation update"].decision.route == ROUTE_PILOT
    assert e["Operations room chat into a situation update"].status != STATUS_FUNDED
    assert sum(x.decision.route == ROUTE_NOT_NOW for x in e.values()) == 2


def test_no_request_wording_appears_in_the_model_code():
    src = (pathlib.Path(__file__).parents[1] / "triage" / "model.py").read_text().lower()
    for t in ("procedure", "meeting", "rental", "purchase order", "donor", "warehouse"):
        assert t not in src
