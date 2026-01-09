{% snapshot snp_mdm_projects %}

{{
    config(
      target_schema='snapshots',
      unique_key='project_id',
      strategy='check',
      check_cols=['project_name', 'status', 'is_active', 'org_id', 'budget_type'],
      invalidate_hard_deletes=True,
    )
}}

select 
    project_id,
    project_name,
    project_type,
    status,
    is_active,
    pm_user_id,
    org_id,
    plan_start_date,
    plan_end_date,
    budget_code,
    budget_type,
    sync_version
from {{ source('raw', 'mdm_projects') }}
where is_current = true

{% endsnapshot %}
