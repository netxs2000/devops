
with source as (
    select * from {{ source('raw', 'mdm_epic') }}
),

renamed as (
    select
        id as epic_id,
        cast(null as varchar) as epic_title,
        cast(null as varchar) as portfolio_link,
        cast(null as jsonb) as epic_labels,
        false as is_capitalizable
    from source
    -- where state = 'open' -- state column is missing
)

select * from renamed
