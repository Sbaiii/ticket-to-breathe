-- Every in-study station must have hourly rows in each coverage year (config.COVERAGE_YEARS).
with expected as (
    select d.sampling_point_id, y.year
    from {{ ref('dim_station') }} as d
    cross join {{ ref('config_coverage_years') }} as y
),

present as (
    select distinct sampling_point_id, year(ts_utc) as year
    from {{ ref('fct_station_hour') }}
)

select e.*
from expected as e
left join present as p using (sampling_point_id, year)
where p.sampling_point_id is null
