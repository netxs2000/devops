
/*
    统一活动流 (Unified Activity Stream) - v3
    
    架构逻辑：
    1. 本模型为视图 (View)，不存储数据。
    2. 它将增量生成的 raw 信号 (int_raw_activities) 与 
       动态更新的身份校准表 (int_identity_alignment) 进行实时关联。
    3. 解决了“身份风暴”：即便某人的 Email 被重新关联到另一个 OneID，
       此处视图查询时会自动指向新的 OneID，无需重跑数百万条历史改增量。
*/

with 

raw_stream as (
    select * from {{ ref('int_raw_activities') }}
),

identities as (
    -- 仅取优先级最高的映射，防止 join 爆炸
    select distinct on (source_system, identifier_type, identifier_value)
        source_system,
        identifier_type,
        identifier_value,
        master_user_id
    from {{ ref('int_identity_alignment') }}
    order by source_system, identifier_type, identifier_value, priority asc
),

golden_users as (
    select * from {{ ref('stg_mdm_identities') }}
),

final as (
    select
        r.*,
        -- 这里的关联是动态的
        coalesce(i.master_user_id, '00000000-0000-0000-0000-000000000000'::uuid) as author_user_id,
        coalesce(u.real_name, 'Unknown') as author_name
    from raw_stream r
    left join identities i 
        on (r.source_system = i.source_system or i.source_system = 'ANY')
        and r.identifier_type = i.identifier_type
        and r.external_author_id = i.identifier_value
    left join golden_users u on i.master_user_id = u.user_id
)

select * from final
