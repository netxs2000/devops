{% snapshot snp_mdm_identities %}

{{
    config(
      target_database='devops_collector',
      target_schema='snapshots',
      unique_key='user_id',
      strategy='check',
      check_cols=['department', 'real_name', 'is_active', 'is_vendor'],
      invalidate_hard_deletes=True,
    )
}}

select 
    global_user_id as user_id,
    email,
    employee_id,
    real_name,
    department,
    is_active,
    is_vendor,
    sync_version
from {{ source('raw', 'mdm_identities') }}
where is_current = true

{% endsnapshot %}
