"""python -m triage serve | report"""
from __future__ import annotations

import argparse

from .memo import build_roadmap
from .model import load_config
from .store import Store


def report() -> str:
    cfg = load_config()
    road = build_roadmap(Store().all(), cfg)
    lines = [f"90-day roadmap, {road['slots']} build slots, "
             f"stability from {road['stability']['runs']} seeded runs", ""]
    for it in road["items"]:
        rank = it["rank"] or "-"
        st = it["stability"]
        stab = f"{st['pct_funded']}% funded" if st.get("pct_funded") is not None else ""
        lines.append(f"{str(rank):>2}  {it['title']:<38} {it['route_label']:<44} "
                     f"{it['status']:<9} {it['priority']:>5} {stab}")
    return "\n".join(lines)


def main() -> None:
    p = argparse.ArgumentParser(prog="triage")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("serve", help="start the web page")
    s.add_argument("--port", type=int, default=8107)
    s.add_argument("--host", default="127.0.0.1")
    sub.add_parser("report", help="print the ranked roadmap")
    a = p.parse_args()
    if a.cmd == "report":
        print(report())
        return
    import uvicorn

    from .app import create_app
    print(f"AI request triage on http://{a.host}:{a.port}")
    uvicorn.run(create_app(), host=a.host, port=a.port, log_level="warning")


if __name__ == "__main__":
    main()
