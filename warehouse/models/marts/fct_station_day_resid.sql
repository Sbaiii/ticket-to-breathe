-- Station × local day outcomes (ADR-007) over the hours that have both an observation and a
-- prediction; only days with at least min_valid_hours_per_day such hours.
--   resid_ugm3 = daily mean observed − daily mean predicted (µg/m³)
--   ratio_pct  = 100 × (sum observed / sum predicted − 1)  → primary outcome;
--                null when sum predicted ≤ 0 (ratio_guarded)
-- The pre-treatment period is defined on local dates, so a day is either fully out-of-fold
-- (is_oof) or fully post-treatment.
with params as (
    select max(case when param = 'min_valid_hours_per_day' then value end)::int as min_hours
    from {{ ref('config_params') }}
),

daily as (
    select
        sampling_point_id,
        local_date,
        count(*) as valid_hours,
        avg(no2) as no2_obs,
        avg(pred_used) as no2_pred,
        sum(no2) as sum_obs,
        sum(pred_used) as sum_pred,
        count(*) filter (where is_oof) as oof_hours,
        count(*) filter (where pred_source = 'noblh') as noblh_hours
    from {{ ref('fct_station_hour_deweathered') }}
    where no2 is not null and pred_used is not null
    group by sampling_point_id, local_date
)

select
    d.sampling_point_id,
    d.local_date,
    s.country_code,
    s.role,
    s.station_type,
    d.valid_hours,
    d.no2_obs,
    d.no2_pred,
    d.no2_obs - d.no2_pred as resid_ugm3,
    case when d.sum_pred > 0 then 100 * (d.sum_obs / d.sum_pred - 1) end as ratio_pct,
    d.sum_pred <= 0 as ratio_guarded,
    d.sum_obs,
    d.sum_pred,
    d.oof_hours = d.valid_hours as is_oof,
    case
        when d.noblh_hours = 0 then 'main'
        when d.noblh_hours = d.valid_hours then 'noblh'
        else 'mixed'
    end as pred_source,
    d.oof_hours,
    d.noblh_hours,
    m.pre_mean_no2
from daily as d
cross join params
inner join {{ ref('dim_station') }} as s on s.sampling_point_id = d.sampling_point_id
inner join {{ ref('stg_deweather__stations') }} as m on m.sampling_point_id = d.sampling_point_id
where d.valid_hours >= params.min_hours
