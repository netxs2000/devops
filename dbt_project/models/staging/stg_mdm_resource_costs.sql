
with source as (
    select * from {{ source('raw', 'mdm_resource_costs') }}
),

renamed as (
    select
        cost_id,
        user_id,
        hourly_rate,
        currency,
        effective_from,
        effective_to,
        is_current
    from source
    where is_current = true
)

select * from renamed
