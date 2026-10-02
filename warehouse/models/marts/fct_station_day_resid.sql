-- Station × local day residuals: days with at least min_valid_hours_per_day hours that have
-- both a valid observation and a prediction. resid_pct is relative to the station's
-- pre-treatment mean NO2.
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
        avg(resid) as resid,
        count(*) filter (where model_used = 'noblh') as noblh_hours,
        avg(no2 - pred_holdout_jja2019) as resid_holdout_jja2019,
        bool_or(is_train) as has_train_hours
    from {{ ref('fct_station_hour_deweathered') }}
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
    d.resid,
    d.resid / m.train_mean_no2 * 100 as resid_pct,
    m.train_mean_no2,
    d.noblh_hours,
    d.resid_holdout_jja2019,
    d.has_train_hours
from daily as d
cross join params
inner join {{ ref('dim_station') }} as s on s.sampling_point_id = d.sampling_point_id
inner join {{ ref('stg_deweather__stations') }} as m on m.sampling_point_id = d.sampling_point_id
where d.valid_hours >= params.min_hours
