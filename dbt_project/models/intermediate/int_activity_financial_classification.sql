
/*
    活动财务分类模型 (Financial Activity Classification)
    
    逻辑：依据活动类型及关联工作项，将研发投入划分为资本化 (CapEx) 和费用化 (OpEx)。
    - CapEx: [Feature, Enhancement, Epic] - 形成无形资产的新功能开发。
    - OpEx: [Bug, Debt, Risk, Support] - 维持现有系统运行的维护支出。
*/

with activities as (
    select * from {{ ref('int_unified_activities') }}
),

work_items as (
    select * from {{ ref('int_unified_work_items') }}
),

classified_activities as (
    select
        a.*,
        -- 核心分类逻辑
        case 
            -- 1. 基于关联工作项类型 (最准确)
            when lower(w.work_item_type) in ('feature', 'story', 'epic', 'requirement') then 'CapEx'
            when lower(w.work_item_type) in ('bug', 'defect', 'incident', 'sub-task', 'task') then 'OpEx'
            
            -- 2. 基于活动元数据关键字 (Commit Message/MR Title)
            when lower(a.metadata->>'title') ~ 'feat|new|add|impl' then 'CapEx'
            when lower(a.metadata->>'title') ~ 'fix|bug|refactor|debt|docs|chore' then 'OpEx'
            
            -- 3. 默认分类 (谨慎原则：默认费用化)
            else 'OpEx'
        end as financial_category
    from activities a
    left join work_items w on a.target_entity_id = w.work_item_id and a.target_entity_type in ('ISSUE', 'MR')
)

select
    *,
    case 
        when financial_category = 'CapEx' then 1.0
        else 0.0
    end as capex_weight
from classified_activities
