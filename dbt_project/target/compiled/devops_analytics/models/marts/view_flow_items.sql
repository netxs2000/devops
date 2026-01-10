/*
    价值流明细视图 (Flow Items View)
    
    提供给 Dashboard 的价值流详情视图，包含状态、类型和耗时。
*/

select
    work_item_id,
    work_item_key,
    source_project_id as project_id,
    title,
    current_status as state, -- 兼容 Dashboard 的 'state' 字段
    work_item_type,
    flow_type,
    created_at,
    closed_at,
    flow_time_days
from "devops_db"."public_intermediate"."int_flow_items"