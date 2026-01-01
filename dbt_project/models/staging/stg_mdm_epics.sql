
with source as (
    select * from {{ source('raw', 'mdm_epic') }}
),

renamed as (
    select
        id as epic_id,
        title as epic_title,
        portfolio_link,
        labels as epic_labels,
        -- Check if it's CapEx via labels (Strategic Tagging)
        case 
            when labels::text ilike '%CapEx%' then true 
            else false 
        end as is_capitalizable
    from source
    where state = 'open'
)

select * from renamed
