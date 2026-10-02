-- One row per study country and local calendar day 2018-2025 with policy flags from the seed.
-- Treatment flags apply to the treated country only (they are DE policies).
with params as (
    select
        max(case when param = 'first_year' then value end)::int as first_year,
        max(case when param = 'last_year' then value end)::int as last_year
    from {{ ref('config_params') }}
),

days as (
    select cast(d as date) as day_date
    from params, range(
        make_date(params.first_year, 1, 1),
        make_date(params.last_year + 1, 1, 1),
        interval 1 day
    ) as t(d)
),

country_days as (
    select c.country_code, c.role, days.day_date
    from {{ ref('config_countries') }} as c cross join days
),

policy as (
    select * from {{ ref('policy_calendar') }} where start_date is not null
),

holidays as (
    select country_code, holiday_date, string_agg(holiday_name, ' / ') as holiday_name
    from {{ ref('public_holidays') }}
    group by all
)

select
    cd.country_code,
    cd.role,
    cd.day_date,
    {% for p in ['nine_euro', 'tankrabatt', 'deutschlandticket'] %}
    exists (
        select 1 from policy as p
        where p.policy = '{{ p }}' and p.country_code = cd.country_code
          and cd.day_date between p.start_date and coalesce(p.end_date, date '9999-12-31')
    ) as is_{{ p }},
    {% endfor %}
    exists (
        select 1 from policy as p
        where p.category = 'fuel_price' and p.country_code = cd.country_code
          and cd.day_date between p.start_date and coalesce(p.end_date, date '9999-12-31')
    ) as is_fuel_price_measure,
    h.holiday_name is not null as is_public_holiday,
    h.holiday_name
from country_days as cd
left join holidays as h
    on h.country_code = cd.country_code and h.holiday_date = cd.day_date
