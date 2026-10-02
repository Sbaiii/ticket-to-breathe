select
    sampling_point_id,
    ts_utc,
    no2_ugm3,
    pred,
    pred_noblh,
    blh_available,
    is_oof,
    cv_fold
from {{ source('raw', 'deweather_predictions') }}
