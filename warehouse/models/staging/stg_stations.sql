select
    sampling_point_id,
    country as country_code,
    role,
    in_study,
    station_type,
    station_area,
    lat,
    lon,
    altitude,
    station_name,
    station_eoi_code,
    municipality,
    timezone as metadata_timezone_label,
    meets_coverage,
    latest_row_tie,
    {% for y in range(2018, 2026) %}cov_{{ y }},{% endfor %}
    n_rows as raw_rows
from {{ source('raw', 'station_candidates') }}
