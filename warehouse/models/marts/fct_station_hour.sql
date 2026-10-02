-- Hourly in-study NO2 with weather (left join: the weather download may still be running)
-- and calendar fields in local civil time.
select
    h.sampling_point_id,
    h.ts_utc,
    h.ts_local,
    cast(h.ts_local as date) as local_date,
    hour(h.ts_local) as local_hour,
    isodow(h.ts_local) as local_isodow,
    month(h.ts_local) as local_month,
    year(h.ts_local) as local_year,
    isodow(h.ts_local) >= 6 as is_weekend,
    coalesce(p.is_public_holiday, false) as is_public_holiday,
    h.country_code,
    h.no2_ugm3,
    h.validity,
    h.verification,
    h.location_id,
    w.ts_utc is not null as has_weather,
    w.temperature_2m,
    w.relative_humidity_2m,
    w.wind_speed_10m,
    w.wind_direction_10m,
    w.precipitation,
    w.surface_pressure,
    w.shortwave_radiation,
    w.cloud_cover,
    w.boundary_layer_height
from {{ ref('int_station_hour_local') }} as h
left join {{ ref('stg_weather_hourly') }} as w
    on w.location_id = h.location_id and w.ts_utc = h.ts_utc
left join {{ ref('int_country_day_policy') }} as p
    on p.country_code = h.country_code and p.day_date = cast(h.ts_local as date)
