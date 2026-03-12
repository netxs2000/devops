
/*
    异构实体对齐引擎 (Fuzzy Entity Resolution Engine)
    
    逻辑：
    1. 获取 GitRepo 原始数据。
    2. 获取 MDM 中的 Entity Topology (标准资产目录)。
    3. 通过多种策略对齐。
*/

with 
repos as (
    select * from {{ ref('stg_gitlab_projects') }}
),

topology as (
    select * from {{ ref('stg_mdm_entity_topology') }}
    where element_type = 'source-code'
),

aligned as (
    select
        r.gitlab_project_id,
        r.project_name,
        r.path_with_namespace,
        -- 使用 COALESCE 尝试多种对齐策略
        coalesce(
            (select t.master_project_id from topology t where t.external_resource_id = r.gitlab_project_id::text limit 1), -- 策略 A: ID 匹配
            (select t.master_project_id from topology t where t.resource_name = r.path_with_namespace limit 1), -- 策略 B: 路径精确匹配 (推荐)
            (select t.master_project_id from topology t where t.resource_name = r.project_name limit 1)         -- 策略 C: 名称精确匹配 (降级)
        ) as master_entity_id,
        
        case 
            when (select t.master_project_id from topology t where t.external_resource_id = r.gitlab_project_id::text limit 1) is not null then 'EXACT_ID'
            when (select t.master_project_id from topology t where t.resource_name = r.path_with_namespace limit 1) is not null then 'EXACT_PATH'
            when (select t.master_project_id from topology t where t.resource_name = r.project_name limit 1) is not null then 'EXACT_NAME'
            else 'UNALIGNED'
        end as alignment_strategy
    from repos r
)

select 
    a.*,
    t.resource_name as master_entity_name,
    t.master_project_id as master_org_id
from aligned a
left join topology t on a.master_entity_id = t.master_project_id
