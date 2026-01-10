with source as (
    select * from "devops_db"."public"."mdm_identities"
),

renamed as (
    select
        global_user_id as user_id,
        primary_email as email,
        employee_id,
        full_name as real_name,
        department_id,
        is_active,
        sync_version
    from source
    where is_current = true  -- Only look at current active records
)

select * from renamed