-- 生产事故与 MTTR 计算中间表
-- 小白版逻辑：只抓取“P1级且在生产环境发现”的 Bug。

with issues as (
    select * from {{ ref('stg_zentao_issues') }}
    where issue_type = 'bug'
),

incidents as (
    select
        issue_unique_id,
        raw_id as zentao_id,
        product_id,
        created_at as incident_created_at,
        closed_at as incident_closed_at,
        priority,
        found_in_environment,
        
        -- 计算恢复时长（小时）
        extract(epoch from (closed_at - created_at)) / 3600.0 as restore_hours
    from issues
    where priority = 1 
      and found_in_environment = '生产环境(单选)'
      and closed_at is not null
)

select * from incidents
