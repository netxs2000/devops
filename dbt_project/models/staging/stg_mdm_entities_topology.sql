
with source as (
    select * from {{ source('raw', 'mdm_entities_topology') }}
),

renamed as (
    select
        entity_id,
        entity_type,
        display_name,
        internal_id,  -- This is the GitLab Project ID or Jira Project Key
        importance,
        owner_org_id,
        lifecycle_stage
    from source
    where is_current = true
)

select * from renamed
