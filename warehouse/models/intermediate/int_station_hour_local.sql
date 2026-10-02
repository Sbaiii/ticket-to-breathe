-- In-study NO2 hours with local civil time (country time zone, incl. summer time).
select
    n.sampling_point_id,
    n.ts_utc,
    timezone(d.time_zone, timezone('UTC', n.ts_utc)) as ts_local,
    n.no2_ugm3,
    n.validity,
    n.verification,
    d.country_code,
    d.location_id
from {{ ref('stg_eea__no2_hourly') }} as n
inner join {{ ref('dim_station') }} as d on d.sampling_point_id = n.sampling_point_id
