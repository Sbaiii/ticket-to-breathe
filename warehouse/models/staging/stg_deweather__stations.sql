select
    sampling_point_id,
    location_id,
    n_train,
    train_mean_no2,
    train_mean_resid,
    insample_r2,
    insample_rmse,
    oot_blh_n,
    oot_blh_r2,
    oot_blh_rmse,
    oot_blh_bias,
    oot_noblh_r2,
    oot_noblh_rmse,
    oot_noblh_bias,
    holdout_n,
    holdout_r2,
    holdout_rmse,
    holdout_bias,
    model_spec
from {{ source('raw', 'deweather_station_summary') }}
where status = 'ok'
