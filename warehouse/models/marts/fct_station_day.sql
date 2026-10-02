-- Station-day panel (local calendar day): mean NO2 on days with enough valid hours,
-- daily weather, calendar and policy flags. This is the unit of the causal estimates (ADR-003).
with params as (
    select max(case when param = 'min_valid_hours_per_day' then value end)::int as min_hours
    from {{ ref('config_params') }}
),

daily as (
    select
        sampling_point_id,
        local_date,
        any_value(country_code) as country_code,
        count(*) as valid_hours,
        avg(no2_ugm3) as no2_ugm3,
        count(*) filter (where has_weather) as weather_hours,
        avg(temperature_2m) as temperature_2m,
        avg(relative_humidity_2m) as relative_humidity_2m,
        avg(wind_speed_10m) as wind_speed_10m,
        -- Vector mean of the wind direction (degrees, 0-360).
        (degrees(atan2(avg(sin(radians(wind_direction_10m))),
                       avg(cos(radians(wind_direction_10m))))) + 360) % 360 as wind_direction_10m,
        sum(precipitation) as precipitation_sum,
        avg(surface_pressure) as surface_pressure,
        avg(shortwave_radiation) as shortwave_radiation,
        avg(cloud_cover) as cloud_cover,
        avg(boundary_layer_height) as boundary_layer_height,
        count(boundary_layer_height) as blh_hours
    from {{ ref('fct_station_hour') }}
    group by sampling_point_id, local_date
)

select
    d.sampling_point_id,
    d.local_date,
    d.country_code,
    s.role,
    s.station_type,
    d.valid_hours,
    d.no2_ugm3,
    d.weather_hours,
    d.temperature_2m,
    d.relative_humidity_2m,
    d.wind_speed_10m,
    d.wind_direction_10m,
    d.precipitation_sum,
    d.surface_pressure,
    d.shortwave_radiation,
    d.cloud_cover,
    d.boundary_layer_height,
    d.blh_hours,
    year(d.local_date) as local_year,
    month(d.local_date) as local_month,
    isodow(d.local_date) as local_isodow,
    isodow(d.local_date) >= 6 as is_weekend,
    p.is_public_holiday,
    p.is_nine_euro,
    p.is_tankrabatt,
    p.is_deutschlandticket,
    p.is_fuel_price_measure,
    p.is_fuel_price_increase
from daily as d
cross join params
inner join {{ ref('dim_station') }} as s on s.sampling_point_id = d.sampling_point_id
left join {{ ref('int_country_day_policy') }} as p
    on p.country_code = d.country_code and p.day_date = d.local_date
where d.valid_hours >= params.min_hours
