-- Hourly observed vs predicted NO2 (ADR-006). pred_used = main model where BLH is available,
-- otherwise the no-BLH companion (2024-01-01 → 2024-06-30).
with p as (
    select
        *,
        case when blh_available then pred else pred_noblh end as pred_used
    from {{ ref('stg_deweather__predictions') }}
)

select
    p.sampling_point_id,
    p.ts_utc,
    h.local_date,
    p.no2_ugm3 as no2,
    p.pred,
    p.pred_noblh,
    p.pred_used,
    case when p.blh_available then 'blh' else 'noblh' end as model_used,
    p.no2_ugm3 - p.pred_used as resid,
    p.pred_holdout_jja2019,
    p.is_train
from p
inner join {{ ref('fct_station_hour') }} as h
    on h.sampling_point_id = p.sampling_point_id and h.ts_utc = p.ts_utc
