"""Deweather hourly NO2 with cross-fitted LightGBM models per study station (ADR-006, ADR-007).

For every in-study station whose weather location is complete:
- cross-fitting on the pre-treatment period (config.DEWEATHER_TRAIN_WINDOWS, local dates): its
  calendar months go round-robin into K folds; each fold model is trained on the other folds minus
  a buffer of config.DEWEATHER_CV_BUFFER_DAYS around every held-out month, and predicts the
  held-out months → an out-of-fold (OOF) prediction for every pre-treatment hour;
- post-treatment prediction = mean of the K fold models;
- the same for the companion model without BLH (used downstream only where BLH is null);
- out-of-time stress test (train 2018–2019, test 2022-01 → 2022-05) for both feature sets;
- hourly and daily validation metrics per station.

Writes, per station, data/processed/deweather/pred/<sampling_point_id>.parquet and
data/processed/deweather/stations/<sampling_point_id>.json; then combines the JSONs into
data/processed/deweather/station_summary.parquet and the skip list into skipped_stations.csv.
Idempotent: a station is skipped when its outputs exist with the same model-spec hash and weather
fingerprint. Reads the dbt warehouse read-only (run `dbt build` before, and again after).

Run: uv run python -m models.deweather [--workers 7]
"""

import argparse
import hashlib
import json
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

import duckdb
import lightgbm as lgb
import numpy as np
import pandas as pd

from pipeline.config import (
    DEWEATHER_CV_BUFFER_DAYS,
    DEWEATHER_CV_FOLDS,
    DEWEATHER_DIR,
    DEWEATHER_MIN_TRAIN_HOURS,
    DEWEATHER_OOT_TEST,
    DEWEATHER_OOT_TRAIN,
    DEWEATHER_TRAIN_WINDOWS,
    LGBM_NUM_TREES,
    LGBM_PARAMS,
    MIN_VALID_HOURS_PER_DAY,
    REPO_ROOT,
    WEATHER_RAW,
    WEATHER_YEARS,
)

WAREHOUSE = REPO_ROOT / "data" / "warehouse.duckdb"
PRED_DIR = DEWEATHER_DIR / "pred"
STATION_DIR = DEWEATHER_DIR / "stations"

BASE_WEATHER = ["temperature_2m", "relative_humidity_2m", "wind_u", "wind_v", "precipitation",
                "surface_pressure", "shortwave_radiation", "cloud_cover", "boundary_layer_height"]
ROLLING = {"wind_u": "wind_u", "wind_v": "wind_v", "blh": "boundary_layer_height",
           "t2m": "temperature_2m", "precip": "precipitation"}
ROLLING_FEATURES = [f"{k}_{w}h" for k in ROLLING for w in (3, 24)]
CALENDAR = ["local_hour", "local_isodow", "local_doy", "is_public_holiday"]
FEATURES = BASE_WEATHER + ROLLING_FEATURES + CALENDAR
BLH_FEATURES = ["boundary_layer_height", "blh_3h", "blh_24h"]
FEATURES_NOBLH = [f for f in FEATURES if f not in BLH_FEATURES]

# Any change to features, parameters or windows changes this hash and forces a refit.
MODEL_SPEC = hashlib.sha256(json.dumps({
    "features": FEATURES, "features_noblh": FEATURES_NOBLH, "params": LGBM_PARAMS,
    "trees": LGBM_NUM_TREES,
    "train": [list(map(str, w)) for w in DEWEATHER_TRAIN_WINDOWS],
    "oot": [str(d) for d in (*DEWEATHER_OOT_TRAIN, *DEWEATHER_OOT_TEST)],
    "cv": [DEWEATHER_CV_FOLDS, DEWEATHER_CV_BUFFER_DAYS], "version": 2,
}, sort_keys=True).encode()).hexdigest()[:12]


def in_windows(dates: pd.Series, windows) -> pd.Series:
    mask = pd.Series(False, index=dates.index)
    for start, end in windows:
        mask |= (dates >= pd.Timestamp(start)) & (dates < pd.Timestamp(end))
    return mask


def pretreatment_months() -> list[pd.Period]:
    """Calendar months of the pre-treatment period, in time order."""
    return [m for start, end in DEWEATHER_TRAIN_WINDOWS
            for m in pd.period_range(start, pd.Timestamp(end) - pd.Timedelta(days=1), freq="M")]


# Month → fold, round-robin in time order (identical for every station).
FOLD_OF_MONTH = {m: i % DEWEATHER_CV_FOLDS for i, m in enumerate(pretreatment_months())}


def fold_masks(local_date: pd.Series, pre: pd.Series, k: int) -> tuple[pd.Series, pd.Series]:
    """(training rows, held-out rows) for fold k. Training drops the held-out months and
    DEWEATHER_CV_BUFFER_DAYS on both sides of each of them."""
    buffer = pd.Timedelta(days=DEWEATHER_CV_BUFFER_DAYS)
    months = [m for m, f in FOLD_OF_MONTH.items() if f == k]
    held = pre & local_date.dt.to_period("M").isin(months)
    excluded = pd.Series(False, index=local_date.index)
    for m in months:
        excluded |= ((local_date >= m.start_time - buffer)
                     & (local_date < (m + 1).start_time + buffer))
    train = pre & ~excluded
    assert not (train & held).any()
    return train, held


def weather_fingerprint(location_id: str) -> tuple[bool, str, int]:
    """(complete, fingerprint, years present) for a location's weather files."""
    files = [WEATHER_RAW / location_id / f"{y}.parquet" for y in WEATHER_YEARS]
    present = [f for f in files if f.exists()]
    sig = ";".join(f"{f.name}:{f.stat().st_size}" for f in present)
    return len(present) == len(files), hashlib.sha256(sig.encode()).hexdigest()[:12], len(present)


def weather_features(con: duckdb.DuckDBPyConnection, location_id: str) -> pd.DataFrame:
    """Hourly weather features for one location. Rolling means use time-based windows, so they
    never bridge the missing 2020–21 years."""
    glob = str(WEATHER_RAW / location_id / "*.parquet")
    rolling = ",\n".join(
        f"avg({col}) over (order by ts_utc range between interval {w - 1} hours preceding "
        f"and current row) as {key}_{w}h"
        for key, col in ROLLING.items() for w in (3, 24)
    )
    return con.execute(f"""
        with w as (
            select timezone('UTC', time_utc) as ts_utc, temperature_2m,
                   relative_humidity_2m::double as relative_humidity_2m,
                   -wind_speed_10m * sin(radians(wind_direction_10m)) as wind_u,
                   -wind_speed_10m * cos(radians(wind_direction_10m)) as wind_v,
                   precipitation, surface_pressure, shortwave_radiation,
                   cloud_cover::double as cloud_cover, boundary_layer_height
            from read_parquet('{glob}')
        )
        select *, {rolling} from w
    """).df()


def station_hours(con: duckdb.DuckDBPyConnection, spid: str) -> pd.DataFrame:
    return con.execute("""
        select ts_utc, local_date::timestamp as local_date, no2_ugm3, local_hour, local_isodow,
               dayofyear(ts_local) as local_doy,
               is_public_holiday::int as is_public_holiday
        from fct_station_hour where sampling_point_id = ?
    """, [spid]).df()


def fit(X: pd.DataFrame, y: pd.Series) -> lgb.Booster:
    return lgb.train(LGBM_PARAMS, lgb.Dataset(X, label=y), num_boost_round=LGBM_NUM_TREES)


def metrics(y: pd.Series, p: np.ndarray) -> dict:
    if len(y) == 0:
        return {"n": 0, "r2": None, "rmse": None, "bias": None}
    resid = y.to_numpy() - p
    ss_tot = float(((y - y.mean()) ** 2).sum())
    return {"n": len(y),
            "r2": 1 - float((resid ** 2).sum()) / ss_tot if ss_tot > 0 else None,
            "rmse": float(np.sqrt((resid ** 2).mean())), "bias": float((p - y.to_numpy()).mean())}


def daily_metrics(local_date: pd.Series, y: pd.Series, p: np.ndarray) -> dict:
    """Metrics on daily means over local days with ≥ MIN_VALID_HOURS_PER_DAY hours."""
    d = pd.DataFrame({"day": local_date.to_numpy(), "y": y.to_numpy(), "p": p}).dropna()
    d = d.groupby("day").agg(n=("y", "size"), y=("y", "mean"), p=("p", "mean"))
    d = d[d["n"] >= MIN_VALID_HOURS_PER_DAY]
    res = metrics(d["y"], d["p"].to_numpy())
    res["corr2"] = float(d["y"].corr(d["p"]) ** 2) if len(d) > 2 else None
    return {f"daily_{k}": v for k, v in res.items()}


def fit_and_score(df: pd.DataFrame, train: pd.Series, test: pd.Series, feats: list[str]) -> dict:
    """Fit on train rows, score on test rows (hourly and daily)."""
    if train.sum() < DEWEATHER_MIN_TRAIN_HOURS or test.sum() == 0:
        return {"n": 0}
    p = fit(df.loc[train, feats], df.loc[train, "no2_ugm3"]).predict(df.loc[test, feats])
    y = df.loc[test, "no2_ugm3"]
    return metrics(y, p) | daily_metrics(df.loc[test, "local_date"], y, p)


def process_location(location_id: str, stations: list[dict], weather_fp: str) -> list[dict]:
    """Cross-fit, validate and predict every station of one weather location."""
    con = duckdb.connect(str(WAREHOUSE), read_only=True)
    wx = weather_features(con, location_id)
    results = []
    for st in stations:
        spid = st["sampling_point_id"]
        t0 = time.time()
        df = station_hours(con, spid).merge(wx, on="ts_utc", how="inner")
        df = df.dropna(subset=["no2_ugm3", *[c for c in BASE_WEATHER if c != "boundary_layer_height"]])
        df = df.reset_index(drop=True)
        pre = in_windows(df["local_date"], DEWEATHER_TRAIN_WINDOWS)
        post = ~pre
        blh_ok = df[BLH_FEATURES].notna().all(axis=1)
        summary = {**st, "location_id": location_id, "model_spec": MODEL_SPEC,
                   "weather_fp": weather_fp, "n_rows_with_weather": len(df),
                   "n_pre": int(pre.sum())}
        folds = [fold_masks(df["local_date"], pre, k) for k in range(DEWEATHER_CV_FOLDS)]
        min_train = min(int(tr.sum()) for tr, _ in folds)
        summary["min_fold_train"] = min_train
        if min_train < DEWEATHER_MIN_TRAIN_HOURS:
            summary["status"] = (f"skipped: smallest fold has {min_train} training hours "
                                 f"< {DEWEATHER_MIN_TRAIN_HOURS}")
            results.append(summary)
            continue

        # Out-of-time stress test (both feature sets).
        oot_tr = pre & in_windows(df["local_date"], [DEWEATHER_OOT_TRAIN])
        oot_te = pre & in_windows(df["local_date"], [DEWEATHER_OOT_TEST])
        for name, feats in (("blh", FEATURES), ("noblh", FEATURES_NOBLH)):
            summary |= {f"oot_{name}_{k}": v
                        for k, v in fit_and_score(df, oot_tr, oot_te, feats).items()}

        # Cross-fitting: OOF on pre-treatment hours, fold-model mean on post-treatment hours.
        pred = np.full(len(df), np.nan)
        pred_noblh = np.full(len(df), np.nan)
        cv_fold = np.full(len(df), -1)
        post_main = post & blh_ok
        pred[post_main.to_numpy()] = 0.0
        pred_noblh[post.to_numpy()] = 0.0
        gains = []
        for k, (tr, held) in enumerate(folds):
            y = df.loc[tr, "no2_ugm3"]
            main = fit(df.loc[tr, FEATURES], y)
            noblh = fit(df.loc[tr, FEATURES_NOBLH], y)
            held_main = held & blh_ok
            pred[held_main.to_numpy()] = main.predict(df.loc[held_main, FEATURES])
            pred_noblh[held.to_numpy()] = noblh.predict(df.loc[held, FEATURES_NOBLH])
            cv_fold[held.to_numpy()] = k
            if post_main.any():
                pred[post_main.to_numpy()] += main.predict(df.loc[post_main, FEATURES]) / DEWEATHER_CV_FOLDS
            if post.any():
                pred_noblh[post.to_numpy()] += (noblh.predict(df.loc[post, FEATURES_NOBLH])
                                                / DEWEATHER_CV_FOLDS)
            g = main.feature_importance(importance_type="gain")
            gains.append(g / g.sum())
        assert (cv_fold[pre.to_numpy()] >= 0).all() and (cv_fold[post.to_numpy()] == -1).all()

        y_pre = df.loc[pre, "no2_ugm3"]
        for name, p in (("blh", pred), ("noblh", pred_noblh)):
            p_pre = p[pre.to_numpy()]
            summary |= {f"oof_{name}_{k}": v for k, v in (
                metrics(y_pre, p_pre) | daily_metrics(df.loc[pre, "local_date"], y_pre, p_pre)
            ).items()}
        summary["pre_mean_no2"] = float(y_pre.mean())
        summary |= {f"gain_{f}": float(g) for f, g in zip(FEATURES, np.mean(gains, axis=0), strict=True)}

        out = pd.DataFrame({
            "sampling_point_id": spid, "ts_utc": df["ts_utc"], "no2_ugm3": df["no2_ugm3"],
            "pred": pred, "pred_noblh": pred_noblh, "blh_available": blh_ok.to_numpy(),
            "is_oof": pre.to_numpy(),
            "cv_fold": pd.array(np.where(cv_fold >= 0, cv_fold, None), dtype="Int8"),
        })
        tmp = PRED_DIR / f"{spid}.parquet.part"
        out.to_parquet(tmp, index=False)
        tmp.replace(PRED_DIR / f"{spid}.parquet")
        summary["status"] = "ok"
        summary["seconds"] = round(time.time() - t0, 1)
        (STATION_DIR / f"{spid}.json").write_text(json.dumps(summary))
        results.append(summary)
    con.close()
    return results


def up_to_date(spid: str, weather_fp: str) -> bool:
    js = STATION_DIR / f"{spid}.json"
    if not (js.exists() and (PRED_DIR / f"{spid}.parquet").exists()):
        return False
    prev = json.loads(js.read_text())
    return prev.get("model_spec") == MODEL_SPEC and prev.get("weather_fp") == weather_fp


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--workers", type=int, default=7)
    args = parser.parse_args()
    t0 = time.time()
    PRED_DIR.mkdir(parents=True, exist_ok=True)
    STATION_DIR.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect(str(WAREHOUSE), read_only=True)
    stations = con.execute("""
        select sampling_point_id, country_code, role, station_type, location_id
        from dim_station order by sampling_point_id
    """).df()
    con.close()

    skipped, jobs, n_current = [], {}, 0
    for loc, grp in stations.groupby("location_id"):
        complete, fp, n_years = weather_fingerprint(loc)
        for st in grp.to_dict("records"):
            if not complete:
                skipped.append({**st, "reason": f"weather incomplete ({n_years}/{len(WEATHER_YEARS)} years)"})
            elif up_to_date(st["sampling_point_id"], fp):
                n_current += 1
            else:
                jobs.setdefault((loc, fp), []).append(
                    {k: st[k] for k in ("sampling_point_id", "country_code", "role", "station_type")})
    n_todo = sum(len(v) for v in jobs.values())
    print(f"Model spec {MODEL_SPEC}: {len(stations)} stations, {n_current} up to date, "
          f"{n_todo} to fit, {len(skipped)} skipped (weather incomplete)")

    done = 0
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(process_location, loc, sts, fp) for (loc, fp), sts in jobs.items()]
        for fut in as_completed(futures):
            for r in fut.result():
                done += 1
                if r["status"] != "ok":
                    skipped.append({**r, "reason": r["status"]})
            print(f"  {done}/{n_todo} stations processed ({time.time() - t0:.0f} s)", flush=True)

    summaries = [json.loads(p.read_text()) for p in sorted(STATION_DIR.glob("*.json"))]
    pd.DataFrame(summaries).to_parquet(DEWEATHER_DIR / "station_summary.parquet", index=False)
    # Drop prediction files of stations that are no longer in the study set.
    keep = set(stations["sampling_point_id"])
    for p in PRED_DIR.glob("*.parquet"):
        if p.stem not in keep:
            p.unlink()
    sk = pd.DataFrame(skipped, columns=["sampling_point_id", "country_code", "role",
                                        "station_type", "location_id", "reason"])
    sk.to_csv(DEWEATHER_DIR / "skipped_stations.csv", index=False)
    print(f"Done in {time.time() - t0:.0f} s: {len(summaries)} stations with predictions, "
          f"{len(sk)} skipped")
    print(sk.groupby(["country_code", "reason"]).size().to_string() if len(sk) else "")


if __name__ == "__main__":
    main()
