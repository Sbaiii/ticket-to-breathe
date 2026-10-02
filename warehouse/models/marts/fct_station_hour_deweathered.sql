-- Hourly observed vs predicted NO2 (ADR-006, ADR-007). Pre-treatment hours carry out-of-fold
-- predictions (is_oof, cv_fold); post-treatment hours carry the mean of the K fold models.
-- pred_used = main model where BLH is available, otherwise the no-BLH companion
-- (2024-01-01 → 2024-06-30).
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
    case when p.blh_available then 'main' else 'noblh' end as pred_source,
    p.no2_ugm3 - p.pred_used as resid,
    p.is_oof,
    p.cv_fold
from p
inner join {{ ref('fct_station_hour') }} as h
    on h.sampling_point_id = p.sampling_point_id and h.ts_utc = p.ts_utc
