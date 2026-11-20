from conftest import make

from triage.model import (ROUTE_AUTOMATION, ROUTE_EXISTING, ROUTE_NOT_NOW, ROUTE_PILOT, RULES, decide,
                          score)


def route(cfg, **kw):
    r = make(**kw)
    return decide(r, score(r, cfg), cfg)


def test_r1_low_value_is_not_now(cfg):
    d = route(cfg, per_week=1, people=2, minutes=10)
    assert (d.route, d.rule) == (ROUTE_NOT_NOW, "R1")


def test_r1_boundary_at_minimum_hours(cfg):
    # language captures 0.5, so the minimum of 25 saved hours is 50 raw hours
    just_under = route(cfg, per_week=1, people=1, minutes=230)      # 49.8 raw
    exactly = route(cfg, per_week=1, people=1, minutes=230.77)      # 50.0 raw
    assert just_under.rule == "R1"
    assert exactly.rule != "R1"


def test_r2_sensitive_and_high_is_not_now_even_with_everything_else_ready(cfg):
    d = route(cfg, data_class="sensitive", consequence="high")
    assert (d.route, d.rule) == (ROUTE_NOT_NOW, "R2")


def test_r2_needs_both_halves(cfg):
    assert route(cfg, data_class="sensitive", consequence="medium").route == ROUTE_PILOT
    assert route(cfg, data_class="personal", consequence="high").route == ROUTE_PILOT


def test_r3_existing_tool_means_train(cfg):
    d = route(cfg, existing_tool="yes")
    assert (d.route, d.rule) == (ROUTE_EXISTING, "R3")


def test_r3_does_not_need_an_owner(cfg):
    assert route(cfg, existing_tool="yes", owner="", success_measurable=False).route == ROUTE_EXISTING


def test_r3_partly_is_not_enough(cfg):
    assert route(cfg, existing_tool="partly").route == ROUTE_PILOT


def test_r4_fixed_steps_is_automation(cfg):
    d = route(cfg, task_kind="fixed_rules")
    assert (d.route, d.rule) == (ROUTE_AUTOMATION, "R4")


def test_r4_fixed_steps_wins_over_an_existing_tool(cfg):
    assert route(cfg, task_kind="fixed_rules", existing_tool="yes").route == ROUTE_AUTOMATION


def test_r4_automation_without_owner_is_not_now(cfg):
    d = route(cfg, task_kind="fixed_rules", owner="")
    assert (d.route, d.rule) == (ROUTE_NOT_NOW, "R4")


def test_r5_pilot_when_ready(cfg):
    d = route(cfg)
    assert (d.route, d.rule) == (ROUTE_PILOT, "R5")
    assert route(cfg, task_kind="mixed").route == ROUTE_PILOT


def test_r5_pilot_needs_owner_and_measurable(cfg):
    for kw, missing in ((dict(owner=""), "owner"), (dict(success_measurable=False), "measurable")):
        d = route(cfg, **kw)
        assert (d.route, d.rule) == (ROUTE_NOT_NOW, "R5")
        assert missing in d.reason
    both = route(cfg, owner="", success_measurable=False)
    assert "owner" in both.reason and "measurable" in both.reason


def test_rules_are_tried_in_order(cfg):
    d = route(cfg, per_week=1, people=1, minutes=10, data_class="sensitive", consequence="high")
    assert d.rule == "R1"


def test_every_rule_is_written_down():
    assert [r[0] for r in RULES] == ["R1", "R2", "R3", "R4", "R5"]
    assert all(r[3] for r in RULES)


def test_drivers_name_two_or_three_answers(cfg):
    for kw in ({}, dict(existing_tool="yes"), dict(task_kind="fixed_rules"), dict(owner="")):
        assert 2 <= len(route(cfg, **kw).drivers) <= 3
