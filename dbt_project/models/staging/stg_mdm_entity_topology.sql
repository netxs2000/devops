
with source as (
    select * from {{ source('raw', 'mdm_entity_topology') }}
),

renamed as (
    select
        id as topology_id,
        system_code,
        external_resource_id,
        resource_name,
        project_id as master_project_id,
        service_id,
        element_type,
        is_active
    from source
    where is_current = true
)

select * from renamed
