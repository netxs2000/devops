{% snapshot snp_mdm_identities %}

{{
    config(
      target_schema='snapshots',
      unique_key='user_id',
      strategy='check',
      check_cols=['department_id', 'real_name', 'is_active'],
      invalidate_hard_deletes=True,
    )
}}

select 
    global_user_id as user_id,
    primary_email as email,
    employee_id,
    full_name as real_name,
    department_id,
    is_active,
    sync_version
from {{ source('raw', 'mdm_identities') }}
where is_current = true

{% endsnapshot %}
