with source as (
    select * from "devops_db"."public"."hr_employees"
),

renamed as (
    select
        employee_id,
        full_name as hr_name,
        department_name as hr_dept,
        job_title,
        status as hr_status,
        updated_at as hr_updated_at
    from source
)

select * from renamed