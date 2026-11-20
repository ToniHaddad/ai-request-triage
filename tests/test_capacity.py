from conftest import make

from triage.model import STATUS_FUNDED, STATUS_NOT_NOW, STATUS_TRAINING, STATUS_WAITLIST, plan


def pilots(n):
    # distinct priorities: more people means more value
    return [make(id=i + 1, people=10 + 10 * i) for i in range(n)]


def by_id(entries):
    return {e.req.id: e for e in entries}


def test_default_capacity_funds_two(cfg):
    out = by_id(plan(pilots(4), cfg))
    funded = sorted(i for i, e in out.items() if e.status == STATUS_FUNDED)
    assert funded == [3, 4]          # the two highest priorities
    assert out[1].status == out[2].status == STATUS_WAITLIST


def test_slots_parameter_moves_the_line(cfg):
    for slots in (0, 1, 3, 4):
        out = plan(pilots(4), cfg, slots=slots)
        assert sum(e.status == STATUS_FUNDED for e in out) == slots


def test_existing_capability_uses_no_slot(cfg):
    reqs = pilots(2) + [make(id=9, existing_tool="yes", people=200)]
    out = by_id(plan(reqs, cfg, slots=2))
    assert out[9].status == STATUS_TRAINING
    assert out[1].status == out[2].status == STATUS_FUNDED


def test_automation_uses_a_slot(cfg):
    reqs = pilots(2) + [make(id=9, task_kind="fixed_rules", people=100)]
    out = by_id(plan(reqs, cfg, slots=2))
    assert out[9].status == STATUS_FUNDED
    assert sum(e.status == STATUS_FUNDED for e in out.values()) == 2


def test_not_now_is_unranked_and_never_funded(cfg):
    reqs = pilots(1) + [make(id=9, owner="")]
    out = by_id(plan(reqs, cfg))
    assert out[9].status == STATUS_NOT_NOW and out[9].rank is None
    assert out[1].rank == 1


def test_ranks_are_by_priority(cfg):
    out = plan(pilots(5), cfg)
    ranked = [e for e in out if e.rank]
    assert [e.rank for e in ranked] == [1, 2, 3, 4, 5]
    assert [e.priority for e in ranked] == sorted((e.priority for e in ranked), reverse=True)


def test_funded_items_get_a_timeline_inside_the_horizon(cfg):
    for e in plan(pilots(3), cfg):
        if e.status == STATUS_FUNDED:
            assert 1 <= e.start_week <= e.end_week <= cfg["capacity"]["horizon_weeks"]
        if e.status == STATUS_WAITLIST:
            assert e.start_week is None
