
with source as (
    select * from {{ source('raw', 'mdm_identities') }}
),

renamed as (
    select
        global_user_id as user_id,
        email,
        employee_id,
        real_name,
        department,
        is_active,
        is_vendor,
        sync_version
    from source
    where is_current = true  -- Only look at current active records
)

select * from renamed
