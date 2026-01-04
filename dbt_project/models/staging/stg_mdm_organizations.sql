
with source as (
    select * from {{ source('raw', 'mdm_organizations') }}
),

renamed as (
    select
        org_id,
        org_name,
        org_level,
        parent_org_id,
        manager_user_id,
        is_active,
        sync_version,
        is_current,
        effective_from,
        effective_to
    from source
    where is_current = true
)

select * from renamed
