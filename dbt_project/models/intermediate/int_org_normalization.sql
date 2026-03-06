
/*
    组织机构 ID 归一化模型 (Organization ID Normalization)
    
    解决痛点：
    1. 同一部门在不同系统有不同编码 (如 CTR-政务研发中心 vs zentao_dept_198)。
    2. “名字对齐”优先级：HR 编码 (CTR-/DEP-) > 禅道编码 (zentao_dept_*)。
*/

with 

raw_orgs as (
    select 
        org_id,
        org_name,
        case 
            when org_id like 'CTR-%' or org_id like 'DEP-%' then 1
            when org_id like 'zentao_dept_%' then 2
            else 3
        end as id_priority
    from {{ ref('stg_mdm_organizations') }}
),

canonical_map as (
    -- 为每个部门名找到唯一的“黄金 ID”
    select distinct on (org_name)
        org_name,
        org_id as canonical_org_id
    from raw_orgs
    order by org_name, id_priority asc, org_id asc
),

final as (
    -- 建立 原始 ID 到 黄金 ID 的映射表
    select
        r.org_id as original_org_id,
        c.canonical_org_id,
        r.org_name
    from raw_orgs r
    join canonical_map c on r.org_name = c.org_name
)

select * from final
