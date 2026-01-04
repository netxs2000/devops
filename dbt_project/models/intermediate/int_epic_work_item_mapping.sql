
/*
    Epic 与工作项关联映射 (Epic to Work Item Mapping)
    
    逻辑：
    通过工作项的关联 ID 或标签，将其映射到战略 Epic。
*/

with 

work_items as (
    select * from {{ ref('int_unified_work_items') }}
),

epics as (
    select * from {{ ref('stg_mdm_epics') }}
),

mapping as (
    select
        w.work_item_id,
        e.epic_id,
        e.is_capitalizable
    from work_items w
    join epics e on w.work_item_key ilike '%' || e.portfolio_link || '%'
    -- 或者如果有专门的关联表，在此左滑 join
)

select * from mapping
