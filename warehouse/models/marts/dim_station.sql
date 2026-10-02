-- Study stations (ADR-002): in_study only, with role, type, area and weather location.
select
    s.sampling_point_id,
    s.country_code,
    s.role,
    s.station_type,
    s.station_area,
    s.lat,
    s.lon,
    s.altitude,
    s.station_name,
    s.station_eoi_code,
    s.municipality,
    c.time_zone,
    m.location_id,
    m.snap_dist_deg
from {{ ref('stg_stations') }} as s
inner join {{ ref('config_countries') }} as c on c.country_code = s.country_code
left join {{ ref('stg_station_weather_map') }} as m on m.sampling_point_id = s.sampling_point_id
where s.in_study
