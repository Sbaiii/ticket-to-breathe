-- time_utc is stored tz-aware in the Parquet files; keep it as a naive UTC timestamp here.
select
    location_id,
    timezone('UTC', time_utc) as ts_utc,
    temperature_2m,
    relative_humidity_2m::double as relative_humidity_2m,
    wind_speed_10m,
    wind_direction_10m::double as wind_direction_10m,
    precipitation,
    surface_pressure,
    shortwave_radiation,
    cloud_cover::double as cloud_cover,
    boundary_layer_height,
    grid_lat,
    grid_lon
from {{ source('raw', 'weather_hourly') }}
