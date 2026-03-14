-- Nexus 自动清理打分系统
-- 小白版逻辑：给每个包打分，分数越高（危险等级越高），就越该被删掉。
-- 满分 100+，分值越高，越像“垃圾”。

with components as (
    select * from {{ ref('stg_nexus_components') }}
    where is_deleted = false and is_current = true
),

assets_agg as (
    select
        component_id,
        sum(file_size_bytes) as total_size_bytes,
        max(last_downloaded_at) as last_downloaded_at,
        count(asset_id) as asset_count
    from {{ ref('stg_nexus_assets') }}
    where is_deleted = false and is_current = true
    group by 1
),

seed_map as (
    select * from {{ ref('seed_nexus_component_map') }}
),

trace_info as (
    select * from {{ ref('int_nexus_commits') }}
),

base_info as (
    select
        c.component_id,
        c.repository_name,
        c.component_group,
        c.component_name,
        c.component_version,
        c.created_at,
        agg.total_size_bytes,
        agg.last_downloaded_at,
        m.mdm_product_id,
        t.commit_sha,
        
        -- --- 打分逻辑开始 ---
        
        -- 1. 是否是“孤儿包”（未在产品资产表中登记）
        case when m.mdm_product_id is null then 40 else 0 end as score_orphan,
        
        -- 2. 是否是“临时包”（Snapshot 库）
        case when lower(c.repository_name) like '%snapshot%' then 30 else 0 end as score_snapshot,
        
        -- 3. 是否是“陈年旧包”（180天没人下过）
        case 
            when agg.last_downloaded_at is null then 50 -- 从来没人下过，最危险
            when agg.last_downloaded_at < (current_date - interval '180 days') then 30
            else 0 
        end as score_idle,
        
        -- 4. 是否“身份不明”（没能关联到 Git 代码提交）
        case when t.commit_sha is null then 20 else 0 end as score_untraced

    from components c
    left join assets_agg agg on c.component_id = agg.component_id
    left join seed_map m
        on (coalesce(c.component_name, '') = coalesce(cast(m.name as {{ dbt.type_string() }}), '') 
            and coalesce(c.component_group, '') = coalesce(cast(m."group" as {{ dbt.type_string() }}), ''))
    left join trace_info t on c.component_id = t.component_id
),

final_scoring as (
    select
        *,
        (score_orphan + score_snapshot + score_idle + score_untraced) as total_risk_score
    from base_info
)

select
    *,
    case 
        when total_risk_score >= 80 then 'CRITICAL_DELETE' -- 高危：建议立即执行硬删除
        when total_risk_score >= 50 then 'WARNING_CLEANUP' -- 中危：建议人工核对或归档
        else 'KEEP_SAFE'                                  -- 安全：核心资产或近期使用过
    end as cleanup_priority_level,
    
    -- 产出一个“清理理由”方便小白理解
    concat_ws(' | ',
        case when score_orphan > 0 then '孤儿包(无主)' end,
        case when score_snapshot > 0 then 'Snapshot库(临时)' end,
        case when score_idle = 50 then '从未被下载' end,
        case when score_idle = 30 then '长时间未下载' end,
        case when score_untraced > 0 then '源码不可溯源' end
    ) as cleanup_reasons_text

from final_scoring
