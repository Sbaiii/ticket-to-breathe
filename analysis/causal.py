"""Causal estimation as pre-registered in ADR-008 → data/processed/results/*.parquet.

Every estimate of the plan, in one run:
- triple differences with a same-season 2018–19 baseline (primary €9-Ticket, switch-off,
  Deutschlandticket), persistence DiDs (with / without country trends), classic TWFE DiD;
- event study (monthly DE × month coefficients, reference = mean of Jan–May 2022) and its
  same-season-adjusted version;
- placebo dates, placebo countries, industrial-station placebo, wild cluster bootstrap by country;
- heterogeneity and robustness runs;
- country-level synthetic control (own implementation, scipy) with placebo-in-space;
- per-country map data.

All regressions: station-day OLS (pyfixest), station FE + date FE, DE × cell dummies; an effect is
a fixed linear combination of the DE × cell coefficients (`gap(cell)` = regression-adjusted
DE − controls difference). SEs two-way clustered by station and country × ISO week.

Results are labelled PROVISIONAL while control stations are missing predictions (weather download).

Run: uv run python -m analysis.causal
"""

import time
from dataclasses import dataclass, field

import duckdb
import numpy as np
import pandas as pd
import pyfixest as pf
from pyfixest.estimation import demean
from scipy import optimize, stats

from pipeline.config import CONTROL_COUNTRIES, DATA_PROCESSED, REPO_ROOT, TREATED

WAREHOUSE = REPO_ROOT / "data" / "warehouse.duckdb"
RESULTS = DATA_PROCESSED / "results"
MAIN_TYPES = ("traffic", "background")
CLUSTERS = "sid+cw"
SEED = 42
N_BOOT = 9_999

# Periods (local months)
P, S, SD = range(1, 6), range(6, 9), range(9, 13)
JA, MD, YEAR = range(1, 5), range(5, 13), range(1, 13)
BASE = (2018, 2019)
PRE_BLOCKS = [(2018, YEAR), (2019, YEAR), (2022, P)]  # 29 pre-treatment months
FUEL_CUT_CONTROLS = ["FR", "NL", "BE", "PL", "CZ"]
NO_FUEL_CUT_CONTROLS = ["AT", "CH"]


# --------------------------------------------------------------------------------------------
# Data
# --------------------------------------------------------------------------------------------
def load_panel(con: duckdb.DuckDBPyConnection, types=MAIN_TYPES) -> pd.DataFrame:
    """Station-day panel with ratio_pct, resid_ugm3 and ratio_noblh (no-BLH prediction for
    every hour, same ≥ 18-hour rule)."""
    types_sql = ", ".join(f"'{t}'" for t in types)
    df = con.execute(f"""
        with noblh as (
            select sampling_point_id, local_date,
                   case when sum(pred_noblh) > 0
                        then 100 * (sum(no2) / sum(pred_noblh) - 1) end as ratio_noblh
            from fct_station_hour_deweathered
            where no2 is not null and pred_noblh is not null
            group by all
            having count(*) >= (select max(case when param = 'min_valid_hours_per_day'
                                               then value end)::int from config_params)
        )
        select r.sampling_point_id, r.local_date::timestamp as local_date, r.country_code,
               r.role, r.station_type, r.ratio_pct, r.resid_ugm3, n.ratio_noblh
        from fct_station_day_resid r
        left join noblh n using (sampling_point_id, local_date)
        where r.station_type in ({types_sql})
    """).df()
    d = df["local_date"]
    iso = d.dt.isocalendar()
    df["year"], df["month"] = d.dt.year, d.dt.month
    df["weekday"] = d.dt.dayofweek < 5
    df["de"] = (df["country_code"] == TREATED).astype(float)
    df["sid"] = pd.factorize(df["sampling_point_id"])[0]
    df["date_id"] = pd.factorize(df["local_date"])[0]
    df["cw"] = pd.factorize(df["country_code"] + "_" + iso["year"].astype(str) + "_"
                            + iso["week"].astype(str))[0]
    df["moy"] = df["month"]
    df["t"] = (d - pd.Timestamp("2018-01-01")).dt.days / 365.25
    return df


def in_blocks(df: pd.DataFrame, blocks) -> pd.Series:
    mask = pd.Series(False, index=df.index)
    for year, months in blocks:
        mask |= (df["year"] == year) & df["month"].isin(list(months))
    return mask


# --------------------------------------------------------------------------------------------
# Linear-combination DiD
# --------------------------------------------------------------------------------------------
@dataclass
class Design:
    """Cells (label → list of (year, months) blocks), weights of the linear combination over cell
    gaps, and reference cells (dropped; gap = 0)."""
    cells: dict[str, list]
    weights: dict[str, float]
    refs: list[str] = field(default_factory=list)


def triple(T: int, W, R, baselines=BASE, tw="W", tr="R") -> Design:
    """[gap(T,W) − gap(T,R)] − mean_b [gap(b,W) − gap(b,R)]."""
    cells = {f"{tw}{T}": [(T, W)], f"{tr}{T}": [(T, R)]}
    weights = {f"{tw}{T}": 1.0, f"{tr}{T}": -1.0}
    for b in baselines:
        cells[f"{tw}{b}"], cells[f"{tr}{b}"] = [(b, W)], [(b, R)]
        weights[f"{tw}{b}"] = -1.0 / len(baselines)
        weights[f"{tr}{b}"] = 1.0 / len(baselines)
    return Design(cells, weights, refs=[f"{tr}{T}"])


def did(post_label: str, post_blocks, pre_label: str, pre_blocks) -> Design:
    """gap(post) − gap(pre)."""
    return Design({post_label: post_blocks, pre_label: pre_blocks},
                  {post_label: 1.0, pre_label: -1.0}, refs=[pre_label])


def assign_cells(df: pd.DataFrame, design: Design) -> pd.DataFrame:
    cell = pd.Series(pd.NA, index=df.index, dtype="object")
    for label, blocks in design.cells.items():
        m = in_blocks(df, blocks)
        if (m & cell.notna()).any():
            raise ValueError(f"cells overlap at {label}")
        cell[m] = label
    out = df[cell.notna()].copy()
    out["cell"] = cell[cell.notna()]
    return out


def estimate(df: pd.DataFrame, design: Design, y: str = "ratio_pct", fe: str = "sid + date_id",
             weights: str | None = None, treated: str = "de") -> dict:
    d = assign_cells(df, design).dropna(subset=[y])
    dummies = []
    for label in design.cells:
        if label in design.refs:
            continue
        col = f"x_{label}"
        d[col] = d[treated] * (d["cell"] == label)
        dummies.append(col)
    fit = pf.feols(f"{y} ~ {' + '.join(dummies)} | {fe}", d, vcov={"CRV1": CLUSTERS},
                   weights=weights)
    names = [str(n) for n in fit._coefnames]
    if names != dummies:
        raise RuntimeError(f"collinear dummies dropped: {set(dummies) - set(names)}")
    w = np.array([design.weights.get(n[2:], 0.0) for n in names])
    beta, V = np.asarray(fit._beta_hat), np.asarray(fit._vcov)
    est, se = float(w @ beta), float(np.sqrt(w @ V @ w))
    tcrit = stats.t.ppf(0.975, fit._df_t)
    return {"estimate": est, "se": se, "ci_low": est - tcrit * se, "ci_high": est + tcrit * se,
            "df_t": float(fit._df_t), "n_stations": int(d["sid"].nunique()),
            "n_treated_stations": int(d.loc[d[treated] == 1, "sid"].nunique()),
            "n_control_stations": int(d.loc[d[treated] == 0, "sid"].nunique()),
            "n_station_days": int(fit._N), "n_dates": int(d["date_id"].nunique()),
            "n_countries": int(d["country_code"].nunique())}


def detrend(df: pd.DataFrame, y: str = "ratio_pct") -> pd.DataFrame:
    """Remove country-specific linear trends fitted on the pre-treatment months only."""
    pre = df[in_blocks(df, PRE_BLOCKS)].dropna(subset=[y])
    ref = CONTROL_COUNTRIES[0]
    fit = pf.feols(f"{y} ~ i(country_code, t, ref='{ref}') | sid + date_id", pre)
    slopes = {ref: 0.0}
    for name, b in zip(fit._coefnames, fit._beta_hat, strict=True):
        slopes[str(name).split("::")[1].split(":")[0]] = float(b)
    out = df.copy()
    out[y] = out[y] - out["country_code"].map(slopes) * out["t"]
    out.attrs["slopes"] = slopes
    return out


# --------------------------------------------------------------------------------------------
# Event study
# --------------------------------------------------------------------------------------------
def event_study(df: pd.DataFrame, y: str = "ratio_pct") -> pd.DataFrame:
    months = sorted({(yr, m) for yr, m in zip(df["year"], df["month"], strict=True)})
    labels = [f"{yr}{m:02d}" for yr, m in months]
    design = Design({lab: [(yr, [m])] for lab, (yr, m) in zip(labels, months, strict=True)},
                    {}, refs=["202201"])
    d = assign_cells(df, design).dropna(subset=[y])
    dummies = [f"x_{lab}" for lab in labels if lab != "202201"]
    for lab in labels:
        if lab != "202201":
            d[f"x_{lab}"] = d["de"] * (d["cell"] == lab)
    fit = pf.feols(f"{y} ~ {' + '.join(dummies)} | sid + date_id", d, vcov={"CRV1": CLUSTERS})
    names = [str(n) for n in fit._coefnames]
    if names != dummies:
        raise RuntimeError("collinear event-study dummies")
    beta, V = np.asarray(fit._beta_hat), np.asarray(fit._vcov)
    k = len(names)
    idx = {n[2:]: i for i, n in enumerate(names)}

    def unit(lab):  # row vector selecting beta of a month (0 for the reference)
        v = np.zeros(k)
        if lab in idx:
            v[idx[lab]] = 1.0
        return v

    ref = np.mean([unit(f"2022{m:02d}") for m in P], axis=0)
    rows_raw, rows_adj = [], []
    for lab in labels:
        rows_raw.append(unit(lab) - ref)
        base = np.mean([unit(f"{b}{lab[4:]}") for b in BASE], axis=0)
        rows_adj.append(unit(lab) - base)
    tcrit = stats.t.ppf(0.975, fit._df_t)
    out = []
    for version, A in (("reference Jan–May 2022", np.array(rows_raw)),
                       ("same-season adjusted", np.array(rows_adj))):
        est = A @ beta
        se = np.sqrt(np.einsum("ij,jk,ik->i", A, V, A))
        out.append(pd.DataFrame({"version": version, "month": pd.to_datetime(labels, format="%Y%m"),
                                 "estimate": est, "se": se, "ci_low": est - tcrit * se,
                                 "ci_high": est + tcrit * se}))
    res = pd.concat(out, ignore_index=True)
    res["outcome"] = y
    res["n_station_days"] = int(fit._N)
    return res


# --------------------------------------------------------------------------------------------
# Wild cluster bootstrap (restricted, Webb weights, clusters = countries)
# --------------------------------------------------------------------------------------------
WEBB = np.array([-np.sqrt(1.5), -1.0, -np.sqrt(0.5), np.sqrt(0.5), 1.0, np.sqrt(1.5)])


def wild_bootstrap(df: pd.DataFrame, design: Design, y: str = "ratio_pct") -> dict:
    d = assign_cells(df, design).dropna(subset=[y]).reset_index(drop=True)
    labels = [lab for lab in design.cells if lab not in design.refs]
    X = np.column_stack([d["de"].to_numpy() * (d["cell"] == lab).to_numpy() for lab in labels])
    YX = np.column_stack([d[y].to_numpy(), X]).astype(float)
    flist = np.column_stack([d["sid"], pd.factorize(d["date_id"])[0]]).astype(np.uint64)
    dm, ok = demean(YX, flist, np.ones(len(d)), tol=1e-10, maxiter=100_000)
    if not ok:
        raise RuntimeError("demeaning did not converge")
    yd, Xd = dm[:, 0], dm[:, 1:]
    w = np.array([design.weights.get(lab, 0.0) for lab in labels])
    XtXi = np.linalg.inv(Xd.T @ Xd)
    beta = XtXi @ (Xd.T @ yd)
    theta = float(w @ beta)
    g = pd.factorize(d["country_code"])[0]
    G = g.max() + 1
    a = XtXi @ w
    XgX = np.array([Xd[g == j].T @ Xd[g == j] for j in range(G)])  # G × k × k
    M = XgX @ a  # G × k

    def scores(u):
        return np.array([Xd[g == j].T @ u[g == j] for j in range(G)])  # G × k

    se0 = float(np.sqrt(((scores(yd - Xd @ beta) @ a) ** 2).sum()))
    rng = np.random.default_rng(SEED)
    v = WEBB[rng.integers(0, 6, size=(N_BOOT, G))]

    def pvalue(theta0: float) -> float:
        beta_r = beta - a * (w @ beta - theta0) / (w @ a)
        S = scores(yd - Xd @ beta_r)  # G × k
        delta = (v @ S) @ XtXi  # B × k   (β* − β_r)
        theta_b = w @ beta_r + delta @ w
        term = v * (S @ a) - delta @ M.T  # B × G
        se_b = np.sqrt((term ** 2).sum(axis=1))
        t_b = (theta_b - theta0) / se_b
        t0 = (theta - theta0) / se0
        return float(np.mean(np.abs(t_b) >= abs(t0)))

    grid = np.linspace(theta - 8 * se0, theta + 8 * se0, 321)
    ps = np.array([pvalue(x) for x in grid])
    inside = grid[ps >= 0.05]
    return {"estimate": theta, "se_country_crv": se0, "p_value": pvalue(0.0),
            "ci_low": float(inside.min()) if len(inside) else np.nan,
            "ci_high": float(inside.max()) if len(inside) else np.nan,
            "ci_at_grid_edge": bool(len(inside) and (ps[0] >= 0.05 or ps[-1] >= 0.05)),
            "n_clusters": int(G), "n_boot": N_BOOT, "weights": "Webb", "seed": SEED}


# --------------------------------------------------------------------------------------------
# Synthetic control
# --------------------------------------------------------------------------------------------
def country_month_series(df: pd.DataFrame, y: str = "ratio_pct") -> pd.DataFrame:
    sm = (df.dropna(subset=[y]).groupby(["country_code", "sampling_point_id", "year", "month"])[y]
            .mean().reset_index())
    cm = sm.groupby(["country_code", "year", "month"])[y].mean().reset_index()
    cm["month_start"] = pd.to_datetime({"year": cm["year"], "month": cm["month"], "day": 1})
    return cm.pivot(index="month_start", columns="country_code", values=y).sort_index()


def sc_fit(y1: np.ndarray, Y0: np.ndarray) -> np.ndarray:
    k = Y0.shape[1]
    res = optimize.minimize(lambda w: np.sum((y1 - Y0 @ w) ** 2), np.full(k, 1 / k),
                            method="SLSQP", bounds=[(0, 1)] * k,
                            constraints=[{"type": "eq", "fun": lambda w: w.sum() - 1}],
                            options={"ftol": 1e-12, "maxiter": 1000})
    return np.clip(res.x, 0, None) / np.clip(res.x, 0, None).sum()


SC_WINDOWS = {"Jun–Aug 2022": [(2022, S)], "May–Dec 2023": [(2023, MD)]}


def synthetic_control(series: pd.DataFrame) -> dict[str, pd.DataFrame]:
    idx = series.index
    yr, mo = idx.year, idx.month
    pre = np.zeros(len(idx), bool)
    for year, months in PRE_BLOCKS:
        pre |= (yr == year) & np.isin(mo, list(months))
    windows = {name: np.any([(yr == y) & np.isin(mo, list(m)) for y, m in blocks], axis=0)
               for name, blocks in SC_WINDOWS.items()}
    units = [TREATED, *[c for c in CONTROL_COUNTRIES if c in series.columns]]
    weights, paths, rmspe = [], [], []
    for variant in ("raw", "demeaned"):
        for unit in units:
            pool = [c for c in units[1:] if c != unit]
            y1, Y0 = series[unit].to_numpy(), series[pool].to_numpy()
            if variant == "demeaned":
                mu1, mu0 = y1[pre].mean(), Y0[pre].mean(axis=0)
                wts = sc_fit(y1[pre] - mu1, Y0[pre] - mu0)
                synth = (Y0 - mu0) @ wts + mu1
            else:
                wts = sc_fit(y1[pre], Y0[pre])
                synth = Y0 @ wts
            gap = y1 - synth
            if unit == TREATED:
                weights += [{"variant": variant, "donor": c, "weight": float(x)}
                            for c, x in zip(pool, wts, strict=True)]
            paths.append(pd.DataFrame({"variant": variant, "unit": unit, "month": idx,
                                       "actual": y1, "synthetic": synth, "gap": gap,
                                       "is_pre": pre}))
            r_pre = float(np.sqrt(np.mean(gap[pre] ** 2)))
            row = {"variant": variant, "unit": unit, "rmspe_pre": r_pre}
            for name, m in windows.items():
                r_post = float(np.sqrt(np.mean(gap[m] ** 2)))
                row[f"rmspe_post {name}"] = r_post
                row[f"ratio {name}"] = r_post / r_pre
                row[f"mean_gap {name}"] = float(gap[m].mean())
            rmspe.append(row)
    rm = pd.DataFrame(rmspe)
    for name in SC_WINDOWS:
        rm[f"rank {name}"] = rm.groupby("variant")[f"ratio {name}"].rank(ascending=False,
                                                                         method="min")
        rm[f"p {name}"] = rm[f"rank {name}"] / rm.groupby("variant")["unit"].transform("count")
    return {"sc_weights": pd.DataFrame(weights), "sc_paths": pd.concat(paths, ignore_index=True),
            "sc_rmspe": rm}


# --------------------------------------------------------------------------------------------
# Map data
# --------------------------------------------------------------------------------------------
def country_map(df: pd.DataFrame, coords: pd.DataFrame) -> pd.DataFrame:
    """Per country: same-season-adjusted change of the mean station-day ratio_pct (no SE)."""
    rows = []
    for name, (T, W, R) in {"Jun–Aug 2022 vs Jan–May 2022": (2022, S, P),
                            "May–Dec 2023 vs Jan–Apr 2023": (2023, MD, JA)}.items():
        for c, g in df.groupby("country_code"):
            def m(year, months, g=g):
                return g.loc[(g["year"] == year) & g["month"].isin(list(months)), "ratio_pct"].mean()
            val = (m(T, W) - m(T, R)) - np.mean([m(b, W) - m(b, R) for b in BASE])
            st = coords[coords["sampling_point_id"].isin(g["sampling_point_id"].unique())]
            rows.append({"window": name, "country_code": c, "value": float(val),
                         "n_stations": int(g["sampling_point_id"].nunique()),
                         "lat": float(st["lat"].mean()), "lon": float(st["lon"].mean())})
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------------------------
def main() -> None:
    t0 = time.time()
    RESULTS.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(WAREHOUSE), read_only=True)
    n_ctrl_study, n_ctrl_pred = con.execute("""
        select count(*), count(*) filter (where sampling_point_id in
               (select distinct sampling_point_id from fct_station_day_resid))
        from dim_station where role = 'control'
    """).fetchone()
    status = "PROVISIONAL" if n_ctrl_pred < n_ctrl_study else "FINAL"
    panel = load_panel(con)
    industrial = load_panel(con, types=("industrial",))
    coords = con.execute("select sampling_point_id, lat, lon from dim_station").df()
    con.close()
    print(f"{status}: {n_ctrl_pred}/{n_ctrl_study} control stations with predictions; "
          f"panel {len(panel):,} station-days, {panel['sid'].nunique()} stations")

    primary = triple(2022, S, P)
    switch_off = triple(2022, SD, P, tw="SD", tr="P")
    dticket = triple(2023, MD, JA, tw="MD", tr="JA")
    rows = []

    def run(family, spec, design, data=panel, y="ratio_pct", **kw):
        t = time.time()
        r = estimate(data, design, y=y, **kw)
        rows.append({"family": family, "spec": spec, "outcome": y, **r})
        print(f"  {family:<22} {spec:<55} {r['estimate']:+8.3f} "
              f"[{r['ci_low']:+.3f}, {r['ci_high']:+.3f}]  ({time.time() - t:.0f} s)", flush=True)

    # Primary and secondary
    run("primary", "€9-Ticket: triple difference (Jun–Aug vs Jan–May 2022)", primary)
    run("primary", "€9-Ticket: triple difference", primary, y="resid_ugm3")
    run("secondary (a)", "switch-off: Sep–Dec vs Jan–May 2022", switch_off)
    run("secondary (a)", "switch-off: Sep–Dec vs Jan–May 2022, controls AT+CH",
        switch_off, data=panel[panel["country_code"].isin([TREATED, *NO_FUEL_CUT_CONTROLS])])
    run("secondary (b)", "Deutschlandticket: May–Dec vs Jan–Apr 2023", dticket)
    trended = detrend(panel)
    for year in (2024, 2025):
        pers = did(f"Y{year}", [(year, YEAR)], "JA2023", [(2023, JA)])
        run("secondary (b)", f"persistence: {year} vs Jan–Apr 2023", pers)
        run("secondary (b)", f"persistence: {year} vs Jan–Apr 2023, country trends", pers,
            data=trended)
    run("secondary (c)", "classic TWFE DiD: Jun–Aug 2022 vs full pre-period (BIASED by pre-trend)",
        did("S2022", [(2022, S)], "PRE", PRE_BLOCKS))

    # Placebo countries (each formula of the decision rule)
    no_de = panel[panel["country_code"] != TREATED].copy()
    for name, design in (("primary", primary), ("switch-off", switch_off),
                         ("Deutschlandticket", dticket)):
        for c in CONTROL_COUNTRIES:
            if c not in set(no_de["country_code"]):
                continue
            data = no_de.assign(fake=(no_de["country_code"] == c).astype(float))
            run(f"placebo country: {name}", c, design, data=data, treated="fake")
    run("placebo industrial", "industrial stations, primary formula", primary, data=industrial)

    # Placebo dates
    run("placebo date", "Jun–Aug 2019 vs Jan–May, baseline 2018", triple(2019, S, P, (2018,)))
    run("placebo date", "Jun–Aug 2018 vs Jan–May, baseline 2019", triple(2018, S, P, (2019,)))
    quarters = {"Jan–Mar": range(1, 4), "Apr–Jun": range(4, 7), "Jul–Sep": range(7, 10),
                "Oct–Dec": range(10, 13)}
    for T, b in ((2018, 2019), (2019, 2018)):
        for qn, q in quarters.items():
            rest = [m for m in YEAR if m not in q]
            run("placebo date", f"{qn} {T} vs rest of {T}, baseline {b}",
                triple(T, q, rest, (b,)))

    # Heterogeneity
    for st in MAIN_TYPES:
        run("heterogeneity", f"{st} stations", primary, data=panel[panel["station_type"] == st])
    run("heterogeneity", "weekdays (Mon–Fri)", primary, data=panel[panel["weekday"]])
    run("heterogeneity", "weekends (Sat–Sun)", primary, data=panel[~panel["weekday"]])

    # Robustness
    run("robustness", "ratio_noblh (no-BLH prediction everywhere)", primary, y="ratio_noblh")
    for c in CONTROL_COUNTRIES:
        run("robustness", f"leave out {c}", primary, data=panel[panel["country_code"] != c])
    run("robustness", "drop FR", primary, data=panel[panel["country_code"] != "FR"])
    n_c = panel.groupby("country_code")["sid"].transform("size")
    run("robustness", "country-balanced weights", primary, data=panel.assign(bw=1.0 / n_c),
        weights="bw")
    run("robustness", "controls with 2022 fuel cuts (FR, NL, BE, PL, CZ)", primary,
        data=panel[panel["country_code"].isin([TREATED, *FUEL_CUT_CONTROLS])])
    run("robustness", "controls without 2022 fuel cuts (AT, CH)", primary,
        data=panel[panel["country_code"].isin([TREATED, *NO_FUEL_CUT_CONTROLS])])
    smoy = Design(primary.cells, primary.weights, refs=["W2022", "R2022"])
    run("robustness", "station × month-of-year FE", smoy, fe="sid^moy + date_id")

    est = pd.DataFrame(rows)
    est["status"] = status
    est.to_parquet(RESULTS / "estimates.parquet", index=False)
    slopes = pd.DataFrame([{"country_code": c, "slope_pp_per_year": s}
                           for c, s in trended.attrs["slopes"].items()])
    slopes["status"] = status
    slopes.to_parquet(RESULTS / "country_trend_slopes.parquet", index=False)

    print("Wild cluster bootstrap ...", flush=True)
    boot = pd.DataFrame([{"spec": "primary", **wild_bootstrap(panel, primary)}])
    boot["status"] = status
    boot.to_parquet(RESULTS / "wild_bootstrap.parquet", index=False)

    print("Event study ...", flush=True)
    es = event_study(panel)
    es["status"] = status
    es.to_parquet(RESULTS / "event_study.parquet", index=False)

    print("Synthetic control ...", flush=True)
    sc = synthetic_control(country_month_series(panel))
    for name, frame in sc.items():
        frame["status"] = status
        frame.to_parquet(RESULTS / f"{name}.parquet", index=False)

    cmap = country_map(panel, coords)
    cmap["status"] = status
    cmap.to_parquet(RESULTS / "country_map.parquet", index=False)

    meta = pd.DataFrame([{"status": status, "control_stations_with_predictions": n_ctrl_pred,
                          "control_stations_in_study": n_ctrl_study,
                          "panel_station_days": len(panel), "runtime_s": round(time.time() - t0)}])
    meta.to_parquet(RESULTS / "run_meta.parquet", index=False)
    print(f"Done in {time.time() - t0:.0f} s → {RESULTS}")


if __name__ == "__main__":
    main()
