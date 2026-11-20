from conftest import make

from triage.model import score


def test_value_arithmetic(cfg):
    # 4 per week x 13 weeks x 10 people x 30 min / 60 = 260 hours; language captures 0.5 -> 130 saved
    s = score(make(), cfg)
    assert s.raw_hours == 260
    assert s.saved_hours == 130
    assert s.value == 130 / 400 * 100


def test_value_is_capped_at_100(cfg):
    assert score(make(people=1000), cfg).value == 100


def test_risk_mixes_data_and_consequence(cfg):
    # internal 25 x 0.6 + medium 50 x 0.4 = 35
    assert score(make(), cfg).risk == 35
    # sensitive 100 x 0.6 + high 100 x 0.4 = 100
    assert score(make(data_class="sensitive", consequence="high"), cfg).risk == 100
    assert score(make(data_class="public", consequence="low"), cfg).risk == 0


def test_effort_adds_systems_kind_and_data(cfg):
    # 2 systems x 12 + language 25 + internal 5 = 54
    assert score(make(), cfg).effort == 54
    assert score(make(systems=5, task_kind="mixed", data_class="sensitive"), cfg).effort == 100  # 125 capped


def test_readiness_is_owner_plus_measurable(cfg):
    assert score(make(), cfg).readiness == 100
    assert score(make(owner=""), cfg).readiness == 50
    assert score(make(owner="  "), cfg).readiness == 50
    assert score(make(success_measurable=False), cfg).readiness == 50
    assert score(make(owner="", success_measurable=False), cfg).readiness == 0


def test_priority_uses_inverse_of_risk_and_effort(cfg):
    s = score(make(), cfg)
    w = cfg["weights"]
    expected = 0.45 * s.value + 0.20 * (100 - s.risk) + 0.15 * (100 - s.effort) + 0.20 * s.readiness
    assert abs(s.priority(w) - expected) < 1e-9
    assert 0 <= s.priority(w) <= 100


def test_priority_normalises_weights(cfg):
    s = score(make(), cfg)
    doubled = {k: v * 2 for k, v in cfg["weights"].items()}
    assert abs(s.priority(doubled) - s.priority(cfg["weights"])) < 1e-9


def test_workings_are_written_out(cfg):
    w = score(make(), cfg).workings
    assert "260 hours" in w["hours"] and "130 h saved" in w["saved"]
