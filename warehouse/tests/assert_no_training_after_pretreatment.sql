-- Leakage guard: every hour used for training lies inside config.DEWEATHER_TRAIN_WINDOWS.
select p.sampling_point_id, p.ts_utc
from {{ ref('stg_deweather__predictions') }} as p
where p.is_train
  and not exists (
      select 1 from {{ ref('config_deweather_train_windows') }} as w
      where p.ts_utc >= w.start_date and p.ts_utc < w.end_date_exclusive
  )
