-- Nexus 资产详情 Staging 层
with source as (
    select * from {{ source('raw', 'nexus_assets') }}
)

select
    cast(id as {{ dbt.type_string() }}) as asset_id,
    cast(component_id as {{ dbt.type_string() }}) as component_id,
    cast(path as {{ dbt.type_string() }}) as asset_path,
    cast(download_url as {{ dbt.type_string() }}) as download_url,
    cast(size_bytes as numeric) as file_size_bytes,
    
    last_modified as last_modified_at,
    last_downloaded as last_downloaded_at,
    
    created_at,
    updated_at,
    is_deleted,
    is_current
from source
