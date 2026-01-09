{% snapshot snp_mdm_organizations %}

{{
    config(
      target_schema='snapshots',
      unique_key='org_id',
      strategy='check',
      check_cols=['org_name', 'parent_org_id', 'org_level', 'manager_user_id', 'is_active'],
      invalidate_hard_deletes=True,
    )
}}

select 
    org_id,
    org_name,
    org_level,
    parent_org_id,
    manager_user_id,
    is_active,
    sync_version
from {{ source('raw', 'mdm_organizations') }}
where is_current = true

{% endsnapshot %}
