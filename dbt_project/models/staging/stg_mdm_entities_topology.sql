
with source as (
    select * from {{ source('raw', 'mdm_entities_topology') }}
),

renamed as (
    select
        entity_id,
        cast(null as varchar) as entity_type,
        cast(null as varchar) as display_name,
        internal_id,  -- This is the GitLab Project ID or Jira Project Key
        cast(null as varchar) as importance,
        cast(null as varchar) as owner_org_id,
        cast(null as varchar) as lifecycle_stage
    from source
    where is_current = true
)

select * from renamed
