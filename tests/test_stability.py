from triage.model import stability
from triage.store import Store


def reqs():
    return Store(":memory:").all()


def test_same_seed_gives_identical_figures(cfg):
    assert stability(reqs(), cfg) == stability(reqs(), cfg)


def test_seeded_figures_for_the_seed_data(cfg):
    s = stability(reqs(), cfg)
    assert s["runs"] == 1000 and s["seed"] == 107 and s["variation"] == 0.2
    items = s["items"]
    assert items[2]["pct_funded"] == 100     # travel-policy questions
    assert items[3]["pct_funded"] == 58      # overdue approval reminders
    assert items[6]["pct_funded"] == 42      # bid comparison summaries
    assert items[7]["pct_funded"] == 0       # candidate shortlist summaries
    assert items[1]["applies"] is False      # training lane, no slot
    assert items[4]["route"] == "not_now"


def test_funded_shares_add_up_to_the_slots(cfg):
    items = stability(reqs(), cfg)["items"]
    assert sum(i.get("pct_funded") or 0 for i in items.values()) == 200   # 2 slots x 100 percent


def test_zero_variation_is_exact(cfg):
    flat = stability(reqs(), cfg, variation=0.0)["items"]
    assert flat[2]["pct_funded"] == 100 and flat[3]["pct_funded"] == 100
    assert flat[6]["pct_funded"] == 0


def test_more_slots_raise_the_figure(cfg):
    a = stability(reqs(), cfg, slots=2)["items"][6]["pct_funded"]
    b = stability(reqs(), cfg, slots=3)["items"][6]["pct_funded"]
    assert b > a
