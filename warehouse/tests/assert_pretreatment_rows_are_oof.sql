-- ADR-007: every pre-treatment row (local date inside config_deweather_train_windows) carries an
-- out-of-fold prediction, and no post-treatment row does. Checked hourly and daily.
with w as (select * from {{ ref('config_deweather_train_windows') }}),

hourly as (
    select
        'hour' as grain,
        sampling_point_id,
        local_date,
        is_oof,
        cv_fold is not null as has_fold,
        exists (
            select 1 from w where local_date >= w.start_date and local_date < w.end_date_exclusive
        ) as is_pre
    from {{ ref('fct_station_hour_deweathered') }}
),

daily as (
    select
        'day' as grain,
        sampling_point_id,
        local_date,
        is_oof,
        is_oof as has_fold,
        exists (
            select 1 from w where local_date >= w.start_date and local_date < w.end_date_exclusive
        ) as is_pre
    from {{ ref('fct_station_day_resid') }}
)

select * from hourly where is_oof != is_pre or has_fold != is_pre
union all
select * from daily where is_oof != is_pre
