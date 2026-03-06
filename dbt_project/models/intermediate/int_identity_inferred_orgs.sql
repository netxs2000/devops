
/*
    身份归属推断模型 (Identity Attribution Inference) - v9
    
    设计逻辑：
    1. 基于行为归因：通过 int_raw_activities 分析各个外部账号在项目中的活跃度。
    2. 穿透对齐：
       Activity (project_id) -> 
       GitLabProject (path_with_namespace) -> 
       EntityTopology (external_resource_id) -> 
       MasterProject -> 
       Organization (org_id)
    3. 解析 Master ID：匹配电子邮件 (EMAIL) 或 外部 ID (EXTERNAL_ID)。
*/

with 

raw_activities as (
    select * from {{ ref('int_raw_activities') }}
),

gitlab_projects as (
    select 
        gitlab_project_id,
        path_with_namespace
    from {{ ref('stg_gitlab_projects') }}
),

topology as (
    -- 资产拓扑：找到 GitLab 项目所对应的业务资产
    select 
        external_resource_id,
        master_project_id
    from {{ ref('stg_mdm_entity_topology') }}
    where system_code like 'gitlab%' and element_type = 'source-code'
),

projects as (
    -- 业务项目：其所属的业务部门
    select 
        project_id as master_project_id,
        org_id
    from {{ source('raw', 'mdm_projects') }}
    where org_id is not null and org_id <> ''
),

mappings as (
    select * from {{ ref('stg_mdm_identity_mappings') }}
),

activity_signals as (
    select
        r.source_system,
        r.identifier_type,
        r.external_author_id,
        p.org_id as inferred_org_id,
        count(*) as activity_count
    from raw_activities r
    join gitlab_projects gp on r.project_id::text = gp.gitlab_project_id::text
    join topology t on t.external_resource_id like '%' || gp.path_with_namespace
    join projects p on t.master_project_id = p.master_project_id
    group by 1, 2, 3, 4
),

ranked_signals as (
    select
        *,
        row_number() over (partition by source_system, identifier_type, external_author_id order by activity_count desc) as rank
    from activity_signals
),

best_signals as (
    select
        s.*,
        m.user_id as global_user_id
    from ranked_signals s
    -- 多模式匹配：根据推断出的 identifier_type 进行关联
    left join mappings m 
        on lower(trim(s.source_system)) = lower(trim(m.source_system))
        and (
            (s.identifier_type = 'EMAIL' and lower(trim(m.external_email)) = lower(trim(s.external_author_id)))
            or 
            (s.identifier_type = 'EXTERNAL_ID' and lower(trim(m.external_user_id)) = lower(trim(s.external_author_id)))
        )
    where rank = 1
)

select 
    global_user_id,
    source_system,
    identifier_type,
    external_author_id,
    inferred_org_id
from best_signals
