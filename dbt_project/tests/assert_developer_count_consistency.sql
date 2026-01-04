-- 验证 DWS 中的开发者数量是否在合理范围内（不超过身份库总量）
-- 如果返回行，则表示测试失败
with dws_devs as (
    select count(distinct developer_id) as cnt from {{ ref('dws_developer_metrics_daily') }}
),
mdm_devs as (
    select count(distinct master_user_id) as cnt from {{ ref('stg_mdm_identities') }}
)
select *
from dws_devs, mdm_devs
where dws_devs.cnt > mdm_devs.cnt
