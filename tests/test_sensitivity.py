from dataclasses import replace

from conftest import make

from triage.model import ROUTE_NOT_NOW, ROUTE_PILOT, plan, variants, what_would_change
from triage.store import Store


def seed():
    return Store(":memory:").all()


def entry(reqs, rid, cfg):
    return next(e for e in plan(reqs, cfg) if e.req.id == rid)


def swap(reqs, rid, new):
    return [new if r.id == rid else r for r in reqs]


def test_variants_are_sorted_cheapest_first():
    costs = [c for c, _, _ in variants(make())]
    assert costs == sorted(costs)
    assert costs[0] == 0.1


def test_missing_success_statement_is_the_smallest_change(cfg):
    reqs = [replace(make(), id=1, success_measurable=False)]
    w = what_would_change(1, reqs, cfg)["route_change"]
    assert w["change"].startswith("success statement: not measurable to measurable")
    assert w["new_route"] == ROUTE_PILOT


def test_ask_anything_cannot_become_a_pilot_by_one_change(cfg):
    # It lacks both an owner and a measurable goal, so no single change makes it a pilot.
    # The cheapest route change is a different route: a tool they already have.
    w = what_would_change(8, seed(), cfg)["route_change"]
    assert w["new_route"] != ROUTE_PILOT and w["change"].startswith("an existing tool")


def test_reported_change_really_flips_the_route(cfg):
    reqs = seed()
    for rid in range(1, 9):
        w = what_would_change(rid, reqs, cfg)["route_change"]
        if w:
            assert w["new_route"] != entry(reqs, rid, cfg).decision.route


def test_nothing_cheaper_changes_the_route(cfg):
    reqs = seed()
    for rid in (2, 3, 5):
        w = what_would_change(rid, reqs, cfg)["route_change"]
        me = next(r for r in reqs if r.id == rid)
        base = entry(reqs, rid, cfg).decision.route
        for cost, text, new in variants(me):
            if cost >= w["cost"]:
                break
            assert entry(swap(reqs, rid, new), rid, cfg).decision.route == base, text


def test_line_change_is_found_and_minimal_for_the_item_just_inside_the_line(cfg):
    reqs = seed()
    w = what_would_change(2, reqs, cfg)       # purchase order rows: second of two slots, narrow margin
    lc = w["line_change"]
    assert w["line_applies"] and lc["new_status"] == "waitlist" and lc["cost"] <= 0.2
    me = next(r for r in reqs if r.id == 2)
    for cost, text, new in variants(me):
        if cost >= lc["cost"]:
            break
        assert entry(swap(reqs, 2, new), 2, cfg).status == "funded", text


def test_line_change_for_waitlisted_item_moves_it_up(cfg):
    w = what_would_change(5, seed(), cfg)
    assert w["line_change"]["new_status"] == "funded"


def test_line_does_not_apply_to_training(cfg):
    w = what_would_change(4, seed(), cfg)
    assert not w["line_applies"] and w["line_change"] is None


def test_missing_owner_is_reversible(cfg):
    reqs = [replace(make(), id=1, owner="")]
    assert entry(reqs, 1, cfg).decision.route == ROUTE_NOT_NOW
    w = what_would_change(1, reqs, cfg)["route_change"]
    assert w["new_route"] == ROUTE_PILOT and "owner" in w["change"]
