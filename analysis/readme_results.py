"""Render the README results block from dashboard/data/headline.json + meta.json.

Replaces everything between <!-- RESULTS:START --> and <!-- RESULTS:END --> in README.md with a
table of the headline estimates, behind a visible PROVISIONAL banner until status = FINAL. Numbers
only; the prose summary is written by the author after the final run.

Run: uv run python -m analysis.readme_results
"""

import json
import re

from pipeline.config import REPO_ROOT

README = REPO_ROOT / "README.md"
DATA = REPO_ROOT / "dashboard" / "data"
START, END = "<!-- RESULTS:START -->", "<!-- RESULTS:END -->"
UNITS = {"ratio_pct": "% pts", "resid_ugm3": "µg/m³", "commute_excess": "% pts"}


def num(v) -> str:
    return "–" if v is None else f"{v:+.2f}"


def links(status: str) -> str:
    """Links to the full reports of the run the block was generated from."""
    if status == "FINAL":
        docs = ["results.md", "diagnostics.md", "deweathering_report.md",
                "provisional_vs_final.md"]
    else:
        docs = ["results_provisional.md", "diagnostics_provisional.md"]
    return ", ".join(f"[`docs/{d}`](docs/{d})" for d in docs)


def render() -> str:
    head = json.loads((DATA / "headline.json").read_text())
    meta = json.loads((DATA / "meta.json").read_text())
    lines = []
    if head["status"] != "FINAL":
        lines += [(f"> **{head['status']} — do not cite.** Only "
                  f"{meta['control_stations_with_predictions']} of "
                  f"{meta['control_stations_in_study']} control stations have deweathered "
                  "predictions so far (weather download incomplete). Every number below will "
                  "change in the final run."), ""]
    lines += [("| Estimate | Outcome | Estimate [95 % CI] | Placebo-country range | Verdict | "
              "Stations DE / controls |"), "|---|---|---|---|---|---|"]
    for r in head["rows"]:
        pl = ("–" if r["placebo_min"] is None
              else f"[{num(r['placebo_min'])}, {num(r['placebo_max'])}]")
        verdict = r["verdict"] + (f" ({r['direction']} NO₂)" if r["verdict"] == "detected" else "")
        lines.append(f"| {r['label']} | {r['outcome']} ({UNITS[r['outcome']]}) | "
                     f"{num(r['estimate'])} [{num(r['ci_low'])}, {num(r['ci_high'])}] | {pl} | "
                     f"{verdict} | {r['n_de']} / {r['n_ctrl']} |")
    lines += ["", ("ratio_pct: observed / deweathered prediction − 1, in percentage points; "
                   "negative = less NO₂ than expected. Verdict = ADR-008 rule (CI excludes 0 and "
                   "outside the placebo-country range); the headline is the ratio_pct verdict, the "
                   "µg/m³ verdicts are a secondary outcome (ADR-010); \"not evaluated\" = outside "
                   f"the rule. Full tables: {links(head['status'])}."),
              "", (f"_Generated from `dashboard/data/headline.json` ({head['generated_utc']}) by "
                  "`analysis/readme_results.py`._")]
    return "\n".join(lines)


def main() -> None:
    text = README.read_text()
    if START not in text or END not in text:
        raise SystemExit(f"README.md is missing the {START} / {END} markers")
    block = f"{START}\n{render()}\n{END}"
    README.write_text(re.sub(re.escape(START) + r".*?" + re.escape(END), lambda _: block, text,
                             flags=re.DOTALL))
    print(f"Updated results block in {README}")


if __name__ == "__main__":
    main()
