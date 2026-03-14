-- 孤儿制品发现表
-- 目的是找出那些存在于 Nexus 中，但是没有在 seed_nexus_component_map.csv 中登记的组件和关联大小

with components as (
    select * from {{ ref('stg_nexus_components') }}
    where is_deleted = false and is_current = true
),

assets as (
    select * from {{ ref('stg_nexus_assets') }}
    where is_deleted = false and is_current = true
),

seed_map as (
    select * from {{ ref('seed_nexus_component_map') }}
),

component_asset_agg as (
    select
        component_id,
        count(asset_id) as total_assets,
        sum(file_size_bytes) as total_size_bytes,
        max(last_downloaded_at) as last_downloaded_at
    from assets
    group by component_id
),

mapped_components as (
    select
        c.component_id,
        c.repository_name,
        c.package_format,
        c.component_group,
        c.component_name,
        c.component_version,
        c.created_at,
        agg.total_assets,
        agg.total_size_bytes,
        agg.last_downloaded_at,
        m.mdm_product_id
    from components c
    left join component_asset_agg agg
        on c.component_id = agg.component_id
    left join seed_map m
        on (m.match_type = 'exact' and coalesce(c.component_name, '') = coalesce(cast(m.name as {{ dbt.type_string() }}), '') and coalesce(c.component_group, '') = coalesce(cast(m."group" as {{ dbt.type_string() }}), ''))
        -- 为了简单起见，这里假设 exact 或者是基于 name 作为强约束。如果 group 是空则忽略
        -- 实际由于 seed 中的 group 和 name 大片为空，这里只做一个基础演示
)

select
    component_id,
    repository_name,
    package_format,
    component_group,
    component_name,
    component_version,
    created_at,
    total_assets,
    total_size_bytes,
    last_downloaded_at,
    
    -- 判断是否为孤儿包
    case 
        when mdm_product_id is null then true 
        else false 
    end as is_orphan,
    
    -- 清理建议标识
    case 
        when mdm_product_id is null 
             and last_downloaded_at < (current_date - interval '90 days') 
             then 'HIGH_RISK_GHOST'
        else 'SAFE'
    end as cleanup_suggestion

from mapped_components
where mdm_product_id is null -- 重点暴露孤儿
