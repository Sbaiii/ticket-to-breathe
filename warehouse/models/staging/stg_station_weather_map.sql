select
    sampling_point_id,
    location_id,
    snap_dist_deg
from {{ source('raw', 'station_weather_location') }}
