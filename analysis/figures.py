"""Figures (PNG, docs/figures/) and case-study data (JSON, dashboard/data/) from the causal results.

Reads data/processed/results/*.parquet (written by analysis/causal.py); computes nothing new.
Every chart title and JSON file carries the run status (PROVISIONAL until all control stations
have predictions).

Run: uv run python -m analysis.figures
"""

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from analysis.causal import RESULTS
from pipeline.config import DOCS, REPO_ROOT, TREATED

FIG_DIR = DOCS / "figures"
JSON_DIR = REPO_ROOT / "dashboard" / "data"
SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
SERIES, MUTED, POLICY = "#2a78d6", "#b9b8b3", "#dce9f9"
NINE_EURO = (pd.Timestamp("2022-06-01"), pd.Timestamp("2022-09-01"))
DTICKET_START = pd.Timestamp("2023-05-01")
END = pd.Timestamp("2026-01-01")


def style(ax) -> None:
    ax.set_facecolor(SURFACE)
    ax.grid(axis="y", color=GRID, lw=0.6)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=8)


def policy_bands(ax, label: bool = False) -> None:
    ax.axvspan(*NINE_EURO, color=POLICY, lw=0)
    ax.axvspan(DTICKET_START, END, color=POLICY, lw=0, alpha=0.6)
    if label:
        y = ax.get_ylim()[1]
        ax.text(NINE_EURO[0], y, " 9-Euro-Ticket\n + Tankrabatt", fontsize=7, color=INK2,
                va="top", ha="left")
        ax.text(DTICKET_START, y, " Deutschlandticket →", fontsize=7, color=INK2, va="top",
                ha="left")


def save(fig, name: str) -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG_DIR / name, dpi=150, facecolor=SURFACE)
    plt.close(fig)


def write_json(name: str, status: str, payload: dict) -> None:
    JSON_DIR.mkdir(parents=True, exist_ok=True)
    (JSON_DIR / name).write_text(json.dumps({"status": status, **payload}, indent=1,
                                            default=str))


def records(df: pd.DataFrame) -> list[dict]:
    out = df.copy()
    for c in out.columns:
        if pd.api.types.is_datetime64_any_dtype(out[c]):
            out[c] = out[c].dt.strftime("%Y-%m")
    return json.loads(out.to_json(orient="records"))


def event_study_fig(es: pd.DataFrame, status: str) -> None:
    versions = list(es["version"].unique())
    fig, axes = plt.subplots(len(versions), 1, figsize=(12, 7), sharex=True, facecolor=SURFACE)
    for ax, v in zip(axes, versions, strict=True):
        style(ax)
        d = es[es["version"] == v]
        ax.axhline(0, color=INK2, lw=0.8)
        for block in (d[d["month"] < "2020-01-01"], d[d["month"] >= "2022-01-01"]):
            ax.fill_between(block["month"], block["ci_low"], block["ci_high"], color=SERIES,
                            alpha=0.18, lw=0)
            ax.plot(block["month"], block["estimate"], color=SERIES, lw=2)
        policy_bands(ax, label=(v == versions[0]))
        ax.set_title(f"{v}", loc="left", fontsize=10, color=INK)
        ax.set_ylabel("DE − controls, % points", fontsize=8, color=INK2)
    fig.suptitle(f"[{status}] Event study: monthly DE − controls gap in ratio_pct, 95 % CI "
                 "(station + date FE; two-way clustered)", x=0.01, ha="left", fontsize=11,
                 color=INK)
    fig.text(0.01, 0.005, "Top: reference = mean of Jan–May 2022. Bottom: each month minus DE's "
             "average gap in the same calendar month of 2018–19. Blue bands: 9-Euro-Ticket "
             "(Jun–Aug 2022, same months as the Tankrabatt fuel tax cut) and Deutschlandticket "
             "(from May 2023). No weather 2020–21.", fontsize=7, color=INK2, wrap=True)
    fig.tight_layout(rect=(0, 0.04, 1, 0.95))
    save(fig, "event_study.png")


def synthetic_control_fig(paths: pd.DataFrame, weights: pd.DataFrame, status: str) -> None:
    variants = list(paths["variant"].unique())
    fig, axes = plt.subplots(len(variants), 2, figsize=(13, 7), sharex=True, facecolor=SURFACE)
    for row, v in zip(axes, variants, strict=True):
        p = paths[paths["variant"] == v]
        de = p[p["unit"] == TREATED]
        w = weights[(weights["variant"] == v) & (weights["weight"] > 0.005)]
        wtxt = ", ".join(f"{c} {x:.2f}" for c, x in zip(w["donor"], w["weight"], strict=True))
        ax = row[0]
        style(ax)
        for block in (de[de["month"] < "2020-01-01"], de[de["month"] >= "2022-01-01"]):
            ax.plot(block["month"], block["actual"], color=SERIES, lw=2)
            ax.plot(block["month"], block["synthetic"], color=INK2, lw=1.5, ls="--")
        policy_bands(ax)
        ax.set_title(f"{v}: Germany (solid) vs synthetic (dashed)", loc="left", fontsize=9,
                     color=INK)
        ax.text(0.01, 0.03, f"weights: {wtxt}", transform=ax.transAxes, fontsize=7, color=INK2)
        ax.set_ylabel("ratio_pct, %", fontsize=8, color=INK2)
        ax = row[1]
        style(ax)
        ax.axhline(0, color=INK2, lw=0.8)
        for unit, g in p.groupby("unit"):
            color, lw = (SERIES, 2) if unit == TREATED else (MUTED, 1)
            for block in (g[g["month"] < "2020-01-01"], g[g["month"] >= "2022-01-01"]):
                ax.plot(block["month"], block["gap"], color=color, lw=lw,
                        zorder=3 if unit == TREATED else 2)
        policy_bands(ax)
        ax.set_title(f"{v}: gap (actual − synthetic); grey = each donor as placebo", loc="left",
                     fontsize=9, color=INK)
    fig.suptitle(f"[{status}] Synthetic control, country level, monthly station-weighted "
                 "ratio_pct (pre-period: 2018–19 + Jan–May 2022)", x=0.01, ha="left",
                 fontsize=11, color=INK)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    save(fig, "synthetic_control.png")


def placebo_fig(est: pd.DataFrame, status: str) -> None:
    prim = est[(est["family"] == "primary") & (est["outcome"] == "ratio_pct")].iloc[0]
    groups = [("placebo country: primary", "placebo countries"),
              ("placebo date", "placebo dates"), ("placebo industrial", "industrial stations")]
    rows = [("primary (€9-Ticket)", "", prim)]
    for fam, label in groups:
        for _, r in est[est["family"] == fam].iterrows():
            rows.append((label, r["spec"], r))
    fig, ax = plt.subplots(figsize=(10, 0.32 * len(rows) + 1.4), facecolor=SURFACE)
    style(ax)
    ax.grid(axis="x", color=GRID, lw=0.6)
    ax.grid(axis="y", visible=False)
    for i, (grp, spec, r) in enumerate(rows):
        y = len(rows) - i
        color = SERIES if grp.startswith("primary") else INK2
        ax.plot([r["ci_low"], r["ci_high"]], [y, y], color=color, lw=1.5)
        ax.plot(r["estimate"], y, "o", color=color, ms=6)
    ax.set_yticks([len(rows) - i for i in range(len(rows))],
                  [f"{g}: {s}" if s else g for g, s, _ in rows], fontsize=7)
    ax.axvline(0, color=INK2, lw=0.8)
    ax.axvline(prim["estimate"], color=SERIES, lw=0.8, ls=":")
    ax.set_xlabel("estimate, % points of ratio_pct (95 % CI)", fontsize=8, color=INK2)
    fig.suptitle(f"[{status}] Primary estimate vs placebos (same triple-difference formula)",
                 x=0.01, ha="left", fontsize=10, color=INK)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    save(fig, "placebos.png")


def main() -> None:
    est = pd.read_parquet(RESULTS / "estimates.parquet")
    status = str(est["status"].iloc[0])
    es = pd.read_parquet(RESULTS / "event_study.parquet")
    paths = pd.read_parquet(RESULTS / "sc_paths.parquet")
    weights = pd.read_parquet(RESULTS / "sc_weights.parquet")
    rmspe = pd.read_parquet(RESULTS / "sc_rmspe.parquet")
    cmap = pd.read_parquet(RESULTS / "country_map.parquet")

    event_study_fig(es, status)
    synthetic_control_fig(paths, weights, status)
    placebo_fig(est, status)

    keep = ["family", "spec", "outcome", "estimate", "ci_low", "ci_high", "n_stations",
            "n_station_days"]
    write_json("event_study.json", status, {
        "outcome": "ratio_pct, DE − controls, % points", "series": records(es.drop(
            columns=["status"]))})
    write_json("synthetic_control.json", status, {
        "weights": records(weights.drop(columns=["status"])),
        "paths": records(paths.drop(columns=["status"])),
        "rmspe": records(rmspe.drop(columns=["status"]))})
    write_json("placebos.json", status, {
        "estimates": records(est[est["family"].str.startswith(("primary", "placebo"))][keep])})
    write_json("country_map.json", status, {
        "definition": "per country: [mean ratio_pct(window) − mean(reference)] minus the same "
                      "change averaged over 2018 and 2019; station-day means, no SE",
        "countries": records(cmap.drop(columns=["status"]))})
    print(f"Wrote figures to {FIG_DIR} and JSON to {JSON_DIR}")


if __name__ == "__main__":
    main()
