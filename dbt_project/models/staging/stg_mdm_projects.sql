
with source as (
    select * from {{ source('raw', 'mdm_projects') }}
),

renamed as (
    select
        id as mdm_project_id,
        project_code,
        project_name,
        project_type,
        status,
        is_active,
        pm_user_id,
        org_id as mdm_org_id,
        plan_start_date,
        plan_end_date,
        budget_code,
        budget_type,
        sync_version,
        is_current,
        effective_from,
        effective_to
    from source
    where is_current = true
)

select * from renamed
