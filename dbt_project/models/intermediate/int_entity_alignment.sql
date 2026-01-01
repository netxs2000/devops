
/*
    异构实体对齐引擎 (Fuzzy Entity Resolution Engine)
    
    逻辑：
    1. 获取 GitRepo 原始数据。
    2. 获取 MDM 中的 Entity Topology (标准资产目录)。
    3. 通过三种策略对齐：
       a. 精确 ID 对齐 (internal_id)
       b. 路径/名称模糊对齐 (Levenshtein/Regex)
       c. 命名空间关联对齐
*/

with 
repos as (
    select * from {{ ref('stg_gitlab_projects') }}
),

topology as (
    select * from {{ ref('stg_mdm_entities_topology') }}
    where entity_type = 'REPO'
),

aligned as (
    select
        r.gitlab_project_id,
        r.project_name,
        -- 使用 COALESCE 尝试多种对齐策略
        coalesce(
            (select t.entity_id from topology t where t.internal_id = r.gitlab_project_id::text), -- 策略 A: ID 匹配
            (select t.entity_id from topology t where t.display_name = r.project_name),         -- 策略 B: 名称精确匹配
            (select t.entity_id from topology t where r.path_with_namespace ilike '%' || t.display_name || '%') -- 策略 C: 路径模糊匹配
        ) as master_entity_id,
        
        case 
            when (select t.entity_id from topology t where t.internal_id = r.gitlab_project_id::text) is not null then 'EXACT_ID'
            when (select t.entity_id from topology t where t.display_name = r.project_name) is not null then 'EXACT_NAME'
            when (select t.entity_id from topology t where r.path_with_namespace ilike '%' || t.display_name || '%') is not null then 'FUZZY_PATH'
            else 'UNALIGNED'
        end as alignment_strategy
    from repos r
)

select 
    a.*,
    t.display_name as master_entity_name,
    t.importance as master_entity_importance,
    t.owner_org_id as master_org_id
from aligned a
left join topology t on a.master_entity_id = t.entity_id
