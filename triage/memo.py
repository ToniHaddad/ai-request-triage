"""Decision memo: the decision, the scores, the answers that drove it, what would change it."""
from __future__ import annotations

from dataclasses import asdict

from .model import (BUILD_ROUTES, ROUTE_LABELS, ROUTE_NOT_NOW, STATUS_FUNDED, plan, stability,
                    what_would_change)

STATUS_TEXT = {
    "funded": "Funded: inside the capacity line",
    "waitlist": "Waitlist: below the capacity line",
    "training": "Training lane: needs no pilot slot",
    "not_now": "Not now",
}


def entry_json(e, stab=None) -> dict:
    sc = e.scores
    d = {
        "id": e.req.id, "team": e.req.team, "office": e.req.office, "title": e.req.title,
        "rank": e.rank, "status": e.status, "status_text": STATUS_TEXT[e.status],
        "route": e.decision.route, "route_label": ROUTE_LABELS[e.decision.route],
        "rule": e.decision.rule, "reason": e.decision.reason,
        "priority": round(e.priority, 1), "start_week": e.start_week, "end_week": e.end_week,
        "scores": {"value": round(sc.value), "risk": round(sc.risk), "effort": round(sc.effort),
                   "readiness": round(sc.readiness), "saved_hours": round(sc.saved_hours),
                   "raw_hours": round(sc.raw_hours)},
    }
    if stab is not None:
        d["stability"] = stab
    return d


def stability_sentence(s: dict, runs: int, slots: int, variation: float) -> str:
    if s["route"] == ROUTE_NOT_NOW:
        return "Not ranked, so there is no ranking to vary. The route comes from thresholds, not weights."
    pct = f"{variation:.0%}".replace("%", " percent")
    if s["applies"]:
        return (f"In the funded top {slots} in {s['pct_funded']} percent of {runs} runs with every weight "
                f"varied by {pct} (seeded). Rank range {s['best_rank']} to {s['worst_rank']}, "
                f"median {s['median_rank']:g}.")
    return (f"This route uses no pilot slot. Across {runs} runs with every weight varied by {pct} (seeded) "
            f"its rank stays between {s['best_rank']} and {s['worst_rank']}, median {s['median_rank']:g}.")


def build_memo(req_id: int, reqs, cfg: dict, slots: int | None = None) -> dict | None:
    slots = cfg["capacity"]["build_slots"] if slots is None else slots
    entries = plan(reqs, cfg, slots=slots)
    e = next((x for x in entries if x.req.id == req_id), None)
    if e is None:
        return None
    stab = stability(reqs, cfg, slots=slots)
    s = stab["items"][req_id]
    change = what_would_change(req_id, reqs, cfg, slots=slots)
    lines = []
    rc, lc = change["route_change"], change["line_change"]
    if rc:
        lines.append({"kind": "route", "text": f"Smallest change that alters the route: {rc['change']}. "
                      f"The route would become: {rc['new_route_label']}.", **rc})
    else:
        lines.append({"kind": "route", "text": "No single-answer change alters the route: it would take several answers changing together (see the reasons above)."})
    if change["line_applies"]:
        if lc:
            verb = "drops below" if e.status == STATUS_FUNDED else "rises above"
            lines.append({"kind": "line", "text": f"Smallest change that moves it across the capacity line: "
                          f"{lc['change']}. It {verb} the line of {slots}.", **lc})
        else:
            lines.append({"kind": "line", "text": "No single-answer change within the search range moves it "
                          "across the capacity line."})
    else:
        lines.append({"kind": "line", "text": "The capacity line does not apply: this route does not use a "
                      "build slot."})
    return {
        "entry": entry_json(e, s), "request": asdict(e.req),
        "workings": e.scores.workings, "drivers": list(e.decision.drivers),
        "change": lines, "stability_text": stability_sentence(s, stab["runs"], slots, stab["variation"]),
        "decision_text": f"{ROUTE_LABELS[e.decision.route]}. {e.decision.reason}",
    }


def build_roadmap(reqs, cfg: dict, slots: int | None = None) -> dict:
    slots = cfg["capacity"]["build_slots"] if slots is None else slots
    entries = plan(reqs, cfg, slots=slots)
    stab = stability(reqs, cfg, slots=slots)
    items = []
    for e in entries:
        j = entry_json(e, stab["items"][e.req.id])
        j["stability_text"] = stability_sentence(stab["items"][e.req.id], stab["runs"], slots, stab["variation"])
        if e.decision.route in BUILD_ROUTES:
            ch = what_would_change(e.req.id, reqs, cfg, slots=slots)
            j["change"] = {"route": ch["route_change"], "line": ch["line_change"]}
        items.append(j)
    return {"slots": slots, "horizon_weeks": cfg["capacity"]["horizon_weeks"], "items": items,
            "stability": {k: stab[k] for k in ("runs", "variation", "seed")}}
