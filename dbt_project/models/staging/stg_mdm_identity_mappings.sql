
with source as (
    select * from {{ source('raw', 'mdm_identity_mappings') }}
),

renamed as (
    select
        id,
        global_user_id as user_id,
        source_system,
        external_user_id,
        external_username,
        external_email
    from source
)

select * from renamed
