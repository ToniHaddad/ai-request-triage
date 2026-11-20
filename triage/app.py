"""FastAPI app: JSON API plus the one self-contained page."""
from __future__ import annotations

from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from .memo import build_memo, build_roadmap
from .model import RULES, ROUTE_LABELS, load_config
from .store import Store

STATIC = Path(__file__).with_name("static")


class Intake(BaseModel):
    team: str = Field(min_length=1, max_length=80)
    office: str = Field(default="Global", max_length=40)
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=600)
    per_week: float = Field(gt=0, le=1000)
    people: int = Field(ge=1, le=100000)
    minutes: float = Field(gt=0, le=10000)
    owner: str = Field(default="", max_length=80)
    data_class: Literal["public", "internal", "personal", "sensitive"]
    success_text: str = Field(default="", max_length=300)
    success_measurable: bool
    existing_tool: Literal["yes", "partly", "no"]
    task_kind: Literal["fixed_rules", "language", "mixed"]
    consequence: Literal["low", "medium", "high"]
    systems: int = Field(default=1, ge=1, le=5)


def create_app(store: Store | None = None, config: dict | None = None) -> FastAPI:
    app = FastAPI(title="AI request triage")
    st = store or Store()
    cfg = config or load_config()

    @app.get("/", response_class=HTMLResponse)
    def page():
        return (STATIC / "index.html").read_text(encoding="utf-8")

    @app.get("/api/config")
    def get_config():
        return {"config": cfg, "route_labels": ROUTE_LABELS,
                "rules": [{"id": r[0], "route": r[1], "title": r[2], "text": r[3]} for r in RULES]}

    @app.get("/api/roadmap")
    def roadmap(slots: int | None = Query(default=None, ge=0, le=8)):
        return build_roadmap(st.all(), cfg, slots)

    @app.get("/api/requests/{rid}/memo")
    def memo(rid: int, slots: int | None = Query(default=None, ge=0, le=8)):
        m = build_memo(rid, st.all(), cfg, slots)
        if m is None:
            raise HTTPException(404, "No such request")
        return m

    @app.post("/api/requests", status_code=201)
    def add(body: Intake):
        return {"id": st.add(body.model_dump())}

    @app.delete("/api/requests/{rid}")
    def delete(rid: int):
        if not st.delete(rid):
            raise HTTPException(404, "No such request")
        return {"deleted": rid}

    @app.post("/api/reset")
    def reset():
        st.reset()
        return {"ok": True}

    return app
