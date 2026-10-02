"""Deweather hourly NO2 with one LightGBM model per study station (ADR-006).

For every in-study station whose weather location is complete:
- main model (all weather features) and companion model without BLH, both trained only on
  pre-treatment hours (config.DEWEATHER_TRAIN_WINDOWS);
- out-of-time validation (train 2018–2019, test 2022-01 → 2022-05) for both models;
- placebo hold-out model (Jun–Aug 2019 removed from training, then predicted);
- predictions for every valid NO2 hour with weather, 2018–2025.

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
    DEWEATHER_DIR,
    DEWEATHER_HOLDOUT,
    DEWEATHER_MIN_TRAIN_HOURS,
    DEWEATHER_OOT_TEST,
    DEWEATHER_OOT_TRAIN,
    DEWEATHER_TRAIN_WINDOWS,
    LGBM_NUM_TREES,
    LGBM_PARAMS,
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
    "holdout": [str(d) for d in DEWEATHER_HOLDOUT], "version": 1,
}, sort_keys=True).encode()).hexdigest()[:12]


def in_windows(ts: pd.Series, windows) -> pd.Series:
    mask = pd.Series(False, index=ts.index)
    for start, end in windows:
        mask |= (ts >= pd.Timestamp(start)) & (ts < pd.Timestamp(end))
    return mask


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
        select ts_utc, no2_ugm3, local_hour, local_isodow, dayofyear(ts_local) as local_doy,
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


def process_location(location_id: str, stations: list[dict], weather_fp: str) -> list[dict]:
    """Fit, validate and predict every station of one weather location."""
    con = duckdb.connect(str(WAREHOUSE), read_only=True)
    wx = weather_features(con, location_id)
    results = []
    for st in stations:
        spid = st["sampling_point_id"]
        t0 = time.time()
        df = station_hours(con, spid).merge(wx, on="ts_utc", how="inner")
        df = df.dropna(subset=[c for c in BASE_WEATHER if c != "boundary_layer_height"])
        train = in_windows(df["ts_utc"], DEWEATHER_TRAIN_WINDOWS) & df["no2_ugm3"].notna()
        summary = {**st, "location_id": location_id, "model_spec": MODEL_SPEC,
                   "weather_fp": weather_fp, "n_rows_with_weather": len(df),
                   "n_train": int(train.sum())}
        if train.sum() < DEWEATHER_MIN_TRAIN_HOURS:
            summary["status"] = f"skipped: {int(train.sum())} training hours < {DEWEATHER_MIN_TRAIN_HOURS}"
            results.append(summary)
            continue
        tr = df[train]
        y = tr["no2_ugm3"]

        # Out-of-time validation (both feature sets).
        oot_tr = in_windows(df["ts_utc"], [DEWEATHER_OOT_TRAIN]) & train
        oot_te = in_windows(df["ts_utc"], [DEWEATHER_OOT_TEST]) & train
        for name, feats in (("blh", FEATURES), ("noblh", FEATURES_NOBLH)):
            if oot_tr.sum() >= DEWEATHER_MIN_TRAIN_HOURS and oot_te.sum() > 0:
                m = fit(df.loc[oot_tr, feats], df.loc[oot_tr, "no2_ugm3"])
                res = metrics(df.loc[oot_te, "no2_ugm3"], m.predict(df.loc[oot_te, feats]))
            else:
                res = metrics(pd.Series(dtype=float), np.array([]))
            summary |= {f"oot_{name}_{k}": v for k, v in res.items()}

        # Final models on all pre-treatment hours.
        main = fit(tr[FEATURES], y)
        noblh = fit(tr[FEATURES_NOBLH], y)
        blh_ok = df[BLH_FEATURES].notna().all(axis=1)
        pred = np.full(len(df), np.nan)
        pred[blh_ok.to_numpy()] = main.predict(df.loc[blh_ok, FEATURES])
        pred_noblh = noblh.predict(df[FEATURES_NOBLH])
        in_sample = main.predict(tr[FEATURES])
        summary |= {f"insample_{k}": v for k, v in metrics(y, in_sample).items()}
        summary["train_mean_no2"] = float(y.mean())
        summary["train_mean_resid"] = float((y - in_sample).mean())
        gain = main.feature_importance(importance_type="gain")
        summary |= {f"gain_{f}": float(g) for f, g in zip(FEATURES, gain / gain.sum(), strict=True)}

        # Placebo hold-out: Jun–Aug 2019 removed from training, then predicted.
        hold = in_windows(df["ts_utc"], [DEWEATHER_HOLDOUT])
        pred_hold = np.full(len(df), np.nan)
        if (hold & df["no2_ugm3"].notna()).sum() > 0:
            m = fit(df.loc[train & ~hold, FEATURES], df.loc[train & ~hold, "no2_ugm3"])
            pred_hold[hold.to_numpy()] = m.predict(df.loc[hold, FEATURES])
            summary |= {f"holdout_{k}": v for k, v in
                        metrics(df.loc[hold, "no2_ugm3"], pred_hold[hold.to_numpy()]).items()}

        out = pd.DataFrame({
            "sampling_point_id": spid, "ts_utc": df["ts_utc"], "no2_ugm3": df["no2_ugm3"],
            "pred": pred, "pred_noblh": pred_noblh, "pred_holdout_jja2019": pred_hold,
            "blh_available": blh_ok.to_numpy(), "is_train": train.to_numpy(),
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
