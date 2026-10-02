select
    country_code,
    "date"::date as stringency_date,
    stringency_index::double as stringency_index
from {{ source('raw', 'oxcgrt_stringency') }}
