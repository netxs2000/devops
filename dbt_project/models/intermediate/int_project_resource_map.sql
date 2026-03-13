
/*
    Unified Project Resource Mapping
    
    Provides a unified lookup table to map external Resource IDs (GitLab, ZenTao, etc.)
     to the Master Project ID in MDM.
*/

with topology as (
    -- 1. 基础拓扑映射 (GitLab, Sonar, ZenTao Projects 等)
    select 
        system_code,
        element_type,
        external_resource_id,
        resource_name,
        master_project_id
    from {{ ref('stg_mdm_entity_topology') }}
    where is_active = true and master_project_id is not null
),

-- 2. 禅道执行/迭代层级展平映射 (递归向上找 Master Project)
zentao_execution_lookup as (
    select 
        'zentao-prod' as system_code,
        'issue-tracker-execution' as element_type,
        execution_id::text as external_resource_id,
        null as resource_name,
        master_project_id
    from {{ ref('int_zentao_execution_hierarchy') }}
),

-- 3. 禅道产品级直接映射 (从 stg_zentao_products 里的 mdm_product_id)
zentao_product_lookup as (
    select
        'zentao-prod' as system_code,
        'issue-tracker-product' as element_type,
        product_id::text as external_resource_id,
        product_name as resource_name,
        mdm_product_id as master_project_id
    from {{ ref('stg_zentao_products') }}
    where mdm_product_id is not null
)

select * from topology
union all
select * from zentao_execution_lookup
union all
select * from zentao_product_lookup
