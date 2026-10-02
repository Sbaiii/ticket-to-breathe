-- The treatment windows in the hand-built policy calendar must equal pipeline/config.py
-- (exported to the config_policy_windows seed by pipeline/build_seeds.py).
select c.policy, c.start_date as config_start, c.end_date as config_end,
       p.start_date as calendar_start, p.end_date as calendar_end
from {{ ref('config_policy_windows') }} as c
left join {{ ref('policy_calendar') }} as p on p.policy = c.policy and p.country_code = 'DE'
where p.policy is null
   or p.start_date is distinct from c.start_date
   or p.end_date is distinct from c.end_date
