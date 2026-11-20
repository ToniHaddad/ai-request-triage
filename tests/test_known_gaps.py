"""Behaviour I found and did not fix. Pinned here so the README's 'Where it fails' stays true."""
from conftest import make

from triage.model import ROUTE_EXISTING, decide, score


def test_rule_r3_ignores_risk(cfg):
    # Sensitive data with a medium consequence scores risk 80 out of 100, yet rule R3
    # still says "use the existing tool and train people". Risk only gates through R2.
    r = make(data_class="sensitive", consequence="medium", existing_tool="yes")
    sc = score(r, cfg)
    assert sc.risk == 80
    assert decide(r, sc, cfg).route == ROUTE_EXISTING
