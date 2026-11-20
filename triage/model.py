"""Scoring, routing, capacity and the 'what would change this' analysis.

Everything here is plain arithmetic over the numbers in config.toml.
"""
from __future__ import annotations

import os
import random
import statistics
import tomllib
from dataclasses import dataclass, replace
from functools import lru_cache
from pathlib import Path

DATA_CLASSES = ("public", "internal", "personal", "sensitive")
CONSEQUENCES = ("low", "medium", "high")
TASK_KINDS = ("fixed_rules", "language", "mixed")
TOOL_ANSWERS = ("yes", "partly", "no")

ROUTE_EXISTING = "existing_training"
ROUTE_PILOT = "agent_pilot"
ROUTE_AUTOMATION = "automation"
ROUTE_NOT_NOW = "not_now"
ROUTE_LABELS = {
    ROUTE_EXISTING: "Use an existing capability and train people",
    ROUTE_PILOT: "Custom agent pilot",
    ROUTE_AUTOMATION: "Scheduled automation, no AI needed",
    ROUTE_NOT_NOW: "Not now",
}
BUILD_ROUTES = (ROUTE_PILOT, ROUTE_AUTOMATION)

# The written rules, in the order they are tried. The first one that fits wins.
RULES = (
    ("R1", ROUTE_NOT_NOW, "Too little to gain",
     "If the expected saving is under the minimum hours per quarter, not now."),
    ("R2", ROUTE_NOT_NOW, "Protection-sensitive data with a high-consequence answer",
     "If the task touches protection-sensitive data and a wrong answer has a high consequence, "
     "not now: it needs a governance review before any tool."),
    ("R3", ROUTE_EXISTING, "A tool they already have can do it",
     "If the task is language work and the team says a tool they already have could do it, "
     "use that capability and train people. No build, no pilot slot."),
    ("R4", ROUTE_AUTOMATION, "Fixed steps, no AI needed",
     "If the task is the same fixed steps every time, build a scheduled automation. "
     "It needs a named owner to keep it running; without one, not now."),
    ("R5", ROUTE_PILOT, "Language work no current tool covers",
     "Otherwise, if the task needs reading or writing text and no current tool covers it, "
     "run a custom agent pilot. A pilot needs a named owner and a measurable success statement; "
     "without both, not now."),
)


# ---------------------------------------------------------------- config

def config_path() -> Path:
    env = os.environ.get("TRIAGE_CONFIG")
    return Path(env) if env else Path(__file__).with_name("config.toml")


@lru_cache(maxsize=4)
def _load(path: str) -> dict:
    with open(path, "rb") as f:
        return tomllib.load(f)


def load_config(path: str | os.PathLike | None = None) -> dict:
    return _load(str(path or config_path()))


# ---------------------------------------------------------------- data

@dataclass(frozen=True)
class Request:
    id: int
    team: str
    office: str
    title: str
    description: str
    per_week: float          # occurrences per person per week
    people: int
    minutes: float           # minutes per occurrence
    owner: str               # empty string means nobody
    data_class: str
    success_text: str
    success_measurable: bool
    existing_tool: str
    task_kind: str
    consequence: str
    systems: int = 1

    @property
    def has_owner(self) -> bool:
        return bool(self.owner.strip())


@dataclass(frozen=True)
class Scores:
    raw_hours: float
    capture: float
    saved_hours: float
    value: float
    risk_data: float
    risk_consequence: float
    risk: float
    effort: float
    effort_parts: tuple
    readiness: float
    workings: dict

    def priority(self, weights: dict) -> float:
        total = sum(weights.values())
        w = {k: v / total for k, v in weights.items()}
        return (w["value"] * self.value + w["risk"] * (100 - self.risk)
                + w["effort"] * (100 - self.effort) + w["readiness"] * self.readiness)


def score(req: Request, cfg: dict) -> Scores:
    v, r, e, rd = cfg["value"], cfg["risk"], cfg["effort"], cfg["readiness"]
    raw = req.per_week * v["weeks_per_quarter"] * req.people * req.minutes / 60
    capture = v["capture"][req.task_kind]
    saved = raw * capture
    value = min(100.0, saved / v["saved_hours_cap"] * 100)

    rdata = r["data"][req.data_class]
    rcons = r["consequence"][req.consequence]
    risk = r["data_weight"] * rdata + r["consequence_weight"] * rcons

    parts = (("systems", req.systems * e["per_system"]),
             ("task kind", e["kind"][req.task_kind]),
             ("data", e["data"][req.data_class]))
    effort = min(100.0, float(sum(p for _, p in parts)))

    readiness = (rd["owner_points"] if req.has_owner else 0) + (
        rd["measurable_points"] if req.success_measurable else 0)

    workings = {
        "hours": (f"{req.per_week:g} per week x {v['weeks_per_quarter']} weeks x {req.people} people "
                  f"x {req.minutes:g} min / 60 = {raw:.0f} hours a quarter"),
        "saved": f"{raw:.0f} h x {capture:g} capture ({req.task_kind}) = {saved:.0f} h saved",
        "value": f"{saved:.0f} h / {v['saved_hours_cap']} h cap x 100 = {value:.0f}",
        "risk": (f"{r['data_weight']:g} x {rdata} ({req.data_class} data) + "
                 f"{r['consequence_weight']:g} x {rcons} ({req.consequence} consequence) = {risk:.0f}"),
        "effort": " + ".join(f"{p} ({n})" for n, p in parts) + f" = {effort:.0f}",
        "readiness": (f"{rd['owner_points'] if req.has_owner else 0} (owner "
                      f"{'named' if req.has_owner else 'nobody'}) + "
                      f"{rd['measurable_points'] if req.success_measurable else 0} (success "
                      f"{'measurable' if req.success_measurable else 'not measurable'}) = {readiness:.0f}"),
    }
    return Scores(raw, capture, saved, value, rdata, rcons, risk, effort, parts, float(readiness), workings)


# ---------------------------------------------------------------- routing

@dataclass(frozen=True)
class Decision:
    route: str
    rule: str
    rule_title: str
    reason: str
    drivers: tuple


def decide(req: Request, sc: Scores, cfg: dict) -> Decision:
    rules = cfg["rules"]
    title = {r[0]: r[2] for r in RULES}

    def d(route, rule, reason, drivers):
        return Decision(route, rule, title[rule], reason, tuple(drivers))

    hours_line = f"Expected saving is {sc.saved_hours:.0f} hours a quarter"
    if sc.saved_hours < rules["min_saved_hours"]:
        return d(ROUTE_NOT_NOW, "R1",
                 f"Saves about {sc.saved_hours:.0f} hours a quarter, under the {rules['min_saved_hours']}-hour minimum.",
                 [f"{hours_line} (minimum {rules['min_saved_hours']})",
                  f"{req.per_week:g} times a week, {req.people} people, {req.minutes:g} minutes each"])
    if req.data_class == "sensitive" and req.consequence == "high":
        return d(ROUTE_NOT_NOW, "R2",
                 "Protection-sensitive data and a high-consequence wrong answer: governance review first.",
                 ["Data touched: protection-sensitive", "A wrong answer has a high consequence",
                  hours_line])
    if req.task_kind != "fixed_rules" and req.existing_tool == "yes":
        return d(ROUTE_EXISTING, "R3",
                 "A tool the team already has covers this language task, so the work is training, not building.",
                 ["Existing tool could do it: yes", f"Task needs language work, not fixed rules ({req.task_kind})",
                  hours_line])
    if req.task_kind == "fixed_rules":
        if req.has_owner:
            return d(ROUTE_AUTOMATION, "R4",
                     "The steps are the same every time, so a scheduled flow does it with no AI.",
                     ["Task kind: the same fixed steps every time", f"Process owner: {req.owner}",
                      hours_line])
        return d(ROUTE_NOT_NOW, "R4",
                 "Fixed steps would suit a scheduled flow, but nobody owns the process to keep it running.",
                 ["Task kind: the same fixed steps every time", "Process owner: nobody", hours_line])
    # language or mixed work, no current tool covers it
    if sc.readiness >= rules["pilot_min_readiness"]:
        return d(ROUTE_PILOT, "R5",
                 "Language work that no current tool covers, with an owner and a measurable goal.",
                 [f"Existing tool could do it: {req.existing_tool}, so nothing current covers it",
                  f"Process owner: {req.owner}, and success is a measurable statement",
                  hours_line])
    missing = []
    if not req.has_owner:
        missing.append("a named process owner")
    if not req.success_measurable:
        missing.append("a measurable success statement")
    return d(ROUTE_NOT_NOW, "R5",
             "Would be a pilot, but it lacks " + " and ".join(missing) + ".",
             [f"Needs a pilot: language work, existing tool: {req.existing_tool}",
              "Lacks " + " and ".join(missing), hours_line])


# ---------------------------------------------------------------- plan

STATUS_FUNDED = "funded"        # build item inside the capacity line
STATUS_WAITLIST = "waitlist"    # build item below the line
STATUS_TRAINING = "training"    # existing capability, no pilot slot used
STATUS_NOT_NOW = "not_now"


@dataclass(frozen=True)
class Entry:
    req: Request
    scores: Scores
    decision: Decision
    priority: float
    rank: int | None
    status: str
    start_week: int | None = None
    end_week: int | None = None


def weeks_for(route: str, sc: Scores, cfg: dict) -> int:
    t = cfg["timeline"]
    if route == ROUTE_PILOT:
        return round(t["pilot_base_weeks"] + t["pilot_effort_weeks"] * sc.effort / 100)
    if route == ROUTE_AUTOMATION:
        return round(t["automation_base_weeks"] + t["automation_effort_weeks"] * sc.effort / 100)
    return t["training_weeks"]


def plan(reqs, cfg: dict, weights: dict | None = None, slots: int | None = None) -> list[Entry]:
    weights = weights or cfg["weights"]
    slots = cfg["capacity"]["build_slots"] if slots is None else slots
    rows = []
    for r in reqs:
        sc = score(r, cfg)
        rows.append((r, sc, decide(r, sc, cfg), sc.priority(weights)))
    eligible = sorted((x for x in rows if x[2].route != ROUTE_NOT_NOW), key=lambda x: (-x[3], x[0].id))
    rank = {x[0].id: i + 1 for i, x in enumerate(eligible)}
    funded, out = 0, {}
    for r, sc, dec, pr in eligible:
        if dec.route in BUILD_ROUTES:
            if funded < slots:
                funded += 1
                status = STATUS_FUNDED
            else:
                status = STATUS_WAITLIST
        else:
            status = STATUS_TRAINING
        start = end = None
        if status in (STATUS_FUNDED, STATUS_TRAINING):
            start, end = 1, min(cfg["capacity"]["horizon_weeks"], weeks_for(dec.route, sc, cfg))
        out[r.id] = Entry(r, sc, dec, pr, rank[r.id], status, start, end)
    for r, sc, dec, pr in rows:
        if dec.route == ROUTE_NOT_NOW:
            out[r.id] = Entry(r, sc, dec, pr, None, STATUS_NOT_NOW)
    ordered = sorted(out.values(), key=lambda e: (e.rank is None, e.rank or 0, e.req.id))
    return ordered


# ---------------------------------------------------------------- stability

def stability(reqs, cfg: dict, slots: int | None = None, runs: int | None = None,
              variation: float | None = None, seed: int | None = None) -> dict:
    """Seeded Monte Carlo: vary every weight by up to +-variation, re-rank, count."""
    s = cfg["stability"]
    runs = runs or s["runs"]
    variation = s["variation"] if variation is None else variation
    seed = s["seed"] if seed is None else seed
    slots = cfg["capacity"]["build_slots"] if slots is None else slots
    rng = random.Random(seed)
    base = cfg["weights"]
    rows = []
    for r in reqs:
        sc = score(r, cfg)
        rows.append((r.id, sc, decide(r, sc, cfg).route))
    eligible = [x for x in rows if x[2] != ROUTE_NOT_NOW]
    in_line = {x[0]: 0 for x in rows}
    ranks = {x[0]: [] for x in eligible}
    for _ in range(runs):
        w = {k: v * rng.uniform(1 - variation, 1 + variation) for k, v in base.items()}
        order = sorted(eligible, key=lambda x: (-x[1].priority(w), x[0]))
        funded = 0
        for i, (rid, _sc, route) in enumerate(order):
            ranks[rid].append(i + 1)
            if route in BUILD_ROUTES:
                if funded < slots:
                    in_line[rid] += 1
                funded += 1
    out = {}
    for rid, _sc, route in rows:
        if route == ROUTE_NOT_NOW:
            out[rid] = {"route": route, "applies": False}
            continue
        rk = sorted(ranks[rid])
        out[rid] = {
            "route": route, "applies": route in BUILD_ROUTES,
            "pct_funded": round(100 * in_line[rid] / runs) if route in BUILD_ROUTES else None,
            "median_rank": statistics.median(rk), "best_rank": rk[0], "worst_rank": rk[-1],
        }
    return {"runs": runs, "variation": variation, "seed": seed, "slots": slots, "items": out}


# ---------------------------------------------------------------- what would change this

_CATEGORICAL = (
    ("owner", None), ("success_measurable", None), ("existing_tool", TOOL_ANSWERS),
    ("data_class", DATA_CLASSES), ("consequence", CONSEQUENCES), ("task_kind", TASK_KINDS),
)
_NUMERIC = (("per_week", "occurrences per person per week"), ("people", "people who do it"),
            ("minutes", "minutes per occurrence"), ("systems", "systems touched"))
_PHRASE = {
    "owner": "owner", "success_measurable": "success statement", "existing_tool": "an existing tool could do it",
    "data_class": "data touched", "consequence": "consequence of a wrong answer", "task_kind": "task kind",
}
_NICE = {
    "fixed_rules": "fixed steps", "language": "language work", "mixed": "language plus fixed steps",
    True: "measurable", False: "not measurable",
}


def _nice(v) -> str:
    return _NICE.get(v, str(v))


def variants(req: Request):
    """Single-answer changes, cheapest first. A changed category costs 1.0; a changed number
    costs its relative size (a 40 percent change costs 0.4)."""
    out = []
    # numbers: relative changes of 10 percent steps, from -90 percent to +300 percent
    for f in range(1, 40):
        for sign in (-1, 1):
            rel = sign * f / 10
            if rel < -0.9:
                continue
            for name, label in _NUMERIC:
                old = getattr(req, name)
                new = old * (1 + rel)
                if name in ("people", "systems"):
                    new = max(1, round(new))
                    if name == "systems" and new > 5:
                        continue
                else:
                    new = round(new, 2)
                if new == old or new <= 0:
                    continue
                shown = f"{new:g}"
                out.append((abs(rel), f"{label}: {old:g} to {shown} ({rel:+.0%})", replace(req, **{name: new})))
    # categories
    if req.has_owner:
        out.append((1.0, "owner: a named person to nobody", replace(req, owner="")))
    else:
        out.append((1.0, "owner: nobody to a named person", replace(req, owner="Named process owner")))
    out.append((1.0, f"success statement: {_nice(req.success_measurable)} to {_nice(not req.success_measurable)}",
                replace(req, success_measurable=not req.success_measurable)))
    for name, options in _CATEGORICAL[2:]:
        for o in options:
            if o != getattr(req, name):
                out.append((1.0, f"{_PHRASE[name]}: {_nice(getattr(req, name))} to {_nice(o)}",
                            replace(req, **{name: o})))
    out.sort(key=lambda x: x[0])
    return out


def what_would_change(req_id: int, reqs, cfg: dict, slots: int | None = None) -> dict:
    reqs = list(reqs)
    base = {e.req.id: e for e in plan(reqs, cfg, slots=slots)}[req_id]
    me = next(r for r in reqs if r.id == req_id)
    route_change = line_change = None
    base_build = base.decision.route in BUILD_ROUTES
    for cost, text, new in variants(me):
        if route_change and (line_change or not base_build):
            break
        alt = {e.req.id: e for e in plan([new if r.id == req_id else r for r in reqs], cfg, slots=slots)}[req_id]
        if alt.decision.route != base.decision.route:
            if not route_change:
                route_change = {"cost": cost, "change": text, "new_route": alt.decision.route,
                                "new_route_label": ROUTE_LABELS[alt.decision.route]}
        elif base_build and alt.status != base.status and not line_change:
            line_change = {"cost": cost, "change": text, "new_status": alt.status}
    return {"route_change": route_change, "line_change": line_change if base_build else None,
            "line_applies": base_build}
