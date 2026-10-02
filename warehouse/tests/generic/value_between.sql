{% test value_between(model, column_name, min_value, max_value) %}
-- Fails for rows where the (non-null) value lies outside [min_value, max_value].
select {{ column_name }}
from {{ model }}
where {{ column_name }} < {{ min_value }} or {{ column_name }} > {{ max_value }}
{% endtest %}
