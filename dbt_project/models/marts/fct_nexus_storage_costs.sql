-- Nexus 存储成本度量事实表
-- 小白版逻辑：把文件大小(Bytes) 换算成 GB，再乘以单价算成钱

with assets as (
    select * from {{ ref('stg_nexus_assets') }}
),

components as (
    select * from {{ ref('stg_nexus_components') }}
),

seed_map as (
    select * from {{ ref('seed_nexus_component_map') }}
),

rates as (
    select * from {{ ref('seed_nexus_storage_rates') }}
),

-- 1. 按组件汇总其下的所有资产大小
component_sizes as (
    select
        component_id,
        sum(file_size_bytes) as total_bytes,
        count(asset_id) as asset_count
    from assets
    group by 1
),

-- 2. 关联组件详情与费率，并进行金额换算
cost_calculation as (
    select
        m.mdm_product_id as product_id,
        c.repository_name,
        c.component_group,
        c.component_name,
        c.component_version as version,
        sz.total_bytes,
        sz.asset_count,
        -- 换算为 GB (1024^3)
        (cast(sz.total_bytes as float) / 1073741824.0) as size_gb,
        -- 匹配费率 (如果库名没匹配上，用 default)
        coalesce(r.price_per_gb_per_month, (select price_per_gb_per_month from rates where repository_type = 'default')) as rate
    from components c
    join component_sizes sz on c.component_id = sz.component_id
    left join seed_map m on c.component_name = cast(m.name as {{ dbt.type_string() }})
    left join rates r on c.repository_name = r.repository_type
    where c.is_deleted = false
)

select
    -- 业务主键
    product_id,
    repository_name,
    component_group,
    component_name,
    version,
    
    -- 度量值
    total_bytes,
    size_gb,
    rate as unit_price_per_gb,
    -- 最终月度预估金额 (GB * 单价)
    round(cast(size_gb * rate as numeric), 4) as estimated_monthly_cost_cny,
    
    -- 审计信息
    now() as calculated_at
from cost_calculation
