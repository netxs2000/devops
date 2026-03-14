-- Nexus 待清理资产行动清单
-- 小白版逻辑：这就是那份“死亡名单”，执行清理脚本会根据这张表去 Nexus 里删东西。

with scoring as (
    select * from {{ ref('int_nexus_cleanup_scoring') }}
)

select
    component_id,
    repository_name,
    component_group,
    component_name,
    component_version,
    total_size_bytes,
    (total_size_bytes / 1073741824.0) as size_gb,
    last_downloaded_at,
    total_risk_score,
    cleanup_priority_level,
    cleanup_reasons_text,
    
    -- 给自动化脚本一个开关：只有 CRITICAL_DELETE 且 空间大于 100MB 的才自动删（安全防范）
    case 
        when cleanup_priority_level = 'CRITICAL_DELETE' and total_size_bytes > 104857600 then true
        else false
    end as is_safe_to_auto_cleanup

from scoring
where cleanup_priority_level != 'KEEP_SAFE'
order by total_risk_score desc, total_size_bytes desc
