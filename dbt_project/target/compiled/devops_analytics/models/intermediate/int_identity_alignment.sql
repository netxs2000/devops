/*
    用户身份校准引擎 (Identity Resolution Engine) - v3
    
    该模型实现了“优先级对齐策略”：
    1. 强关联优先：手动维护或系统导出的 mdm_identity_mappings (EXACT_MAPPING)。
    2. Email 回退：若无强关联，则基于 Email 进行精确对齐 (EMAIL_FALLBACK)。
    
    优先级 (Priority):
    - 10: EXACT_MAPPING (Strong)
    - 20: EMAIL_FALLBACK (Weak/Predictive)
*/

with 

identities as (
    select * from "devops_db"."public_intermediate"."int_golden_identity"
),

mappings as (
    select * from "devops_db"."public_staging"."stg_mdm_identity_mappings"
),

-- 碎片池：将所有映射打平并标记策略
fragment_pool as (
    -- 1. 基于 Mappings 的强关联 (EXTERNAL_ID)
    select 
        source_system,
        'EXTERNAL_ID' as identifier_type,
        external_user_id as identifier_value,
        user_id as master_user_id,
        'EXACT_MAPPING' as strategy,
        10 as priority
    from mappings
    where external_user_id is not null

    union all

    -- 2. 基于 Mappings 的强关联 (EMAIL)
    select 
        source_system,
        'EMAIL' as identifier_type,
        external_email as identifier_value,
        user_id as master_user_id,
        'EXACT_MAPPING' as strategy,
        10 as priority
    from mappings
    where external_email is not null

    union all

    -- 3. 基于 Mappings 的强关联 (USERNAME)
    select 
        source_system,
        'USERNAME' as identifier_type,
        external_username as identifier_value,
        user_id as master_user_id,
        'EXACT_MAPPING' as strategy,
        10 as priority
    from mappings
    where external_username is not null

    union all

    -- 4. 基于 MDM Identities 的 Email 回退策略 (通用自动计算)
    select 
        'ANY' as source_system,
        'EMAIL' as identifier_type,
        primary_email as identifier_value,
        global_user_id as master_user_id,
        'EMAIL_FALLBACK' as strategy,
        20 as priority
    from identities
    where primary_email is not null

    union all

    -- 5. 自动规则：基于 Email 前缀匹配用户名 (Username Auto-Guess)
    -- 场景：Jenkins/Jira 账号名为 zhangsan，而主 Email 为 zhangsan@company.com
    select 
        'ANY' as source_system,
        'USERNAME' as identifier_type,
        split_part(primary_email, '@', 1) as identifier_value,
        global_user_id as master_user_id,
        'USERNAME_AUTO_MATCH' as strategy,
        30 as priority -- 优先级低于精确映射和直接 Email 匹配
    from identities
    where primary_email like '%@%'
)

select * from fragment_pool