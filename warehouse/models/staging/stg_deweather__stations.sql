select
    sampling_point_id,
    location_id,
    n_pre,
    pre_mean_no2,
    min_fold_train,
    oof_blh_r2,
    oof_blh_rmse,
    oof_blh_bias,
    oof_blh_daily_r2,
    oof_blh_daily_corr2,
    oof_blh_daily_rmse,
    oof_noblh_r2,
    oof_noblh_daily_r2,
    oot_blh_r2,
    oot_blh_bias,
    oot_blh_daily_r2,
    oot_noblh_r2,
    model_spec
from {{ source('raw', 'deweather_station_summary') }}
where status = 'ok'
