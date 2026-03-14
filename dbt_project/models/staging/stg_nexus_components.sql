-- Nexus 组件 Staging 层
with source as (
    select * from {{ source('raw', 'nexus_components') }}
)

select
    cast(id as {{ dbt.type_string() }}) as component_id,
    cast(repository as {{ dbt.type_string() }}) as repository_name,
    cast(format as {{ dbt.type_string() }}) as package_format,
    cast("group" as {{ dbt.type_string() }}) as component_group,
    cast(name as {{ dbt.type_string() }}) as component_name,
    cast(version as {{ dbt.type_string() }}) as component_version,
    cast(commit_sha as {{ dbt.type_string() }}) as commit_sha,
    
    created_at,
    updated_at,
    is_deleted,
    is_current
from source
