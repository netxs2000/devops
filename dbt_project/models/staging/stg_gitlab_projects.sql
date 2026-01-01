
with source as (
    select * from {{ source('raw', 'gitlab_projects') }}
),

renamed as (
    select
        id as gitlab_project_id,
        name as project_name,
        path_with_namespace,
        description,
        created_at,
        last_activity_at,
        visibility,
        archived as is_archived
    from source
)

select * from renamed
