select
    sampling_point_id,
    ts_utc,
    no2_ugm3,
    pred,
    pred_noblh,
    pred_holdout_jja2019,
    blh_available,
    is_train
from {{ source('raw', 'deweather_predictions') }}
