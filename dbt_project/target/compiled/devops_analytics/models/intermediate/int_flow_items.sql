/*
    统一价值流项 (Unified Flow Items)
    
    将工作项分类为 Flow Framework 的四种类型：
    - Feature: 业务功能
    - Defect: 缺陷/Bug
    - Debt: 技术债/重构
    - Risk: 风险/安全/合规
*/

with 

base_items as (
    select * from "devops_db"."public_intermediate"."int_unified_work_items"
)

select
    *,
    -- 核心价值分类逻辑
    case 
        when work_item_type in ('Bug', 'Defect', 'Incident') then 'Defect'
        when work_item_type in ('Refactor', 'Tech Debt', 'Cleanup') then 'Debt'
        when work_item_type in ('Security', 'Compliance', 'Risk') then 'Risk'
        else 'Feature'
    end as flow_type,
    
    -- Flow Time 计算 (天)
    extract(epoch from (closed_at - created_at)) / 86400.0 as flow_time_days

from base_items