
/*
    项目交付健康度全景 (Project Delivery Health 360)
    
    该模型是交付体系的“上帝视角”，整合了：
    1. 产出吞吐 (Throughput): MR, Commits
    2. 质量风险 (Quality): Sonar Bugs, Tech Debt
    3. 交付节奏 (Pace): Deployment Freq
    4. 活跃度 (Liveliness): Last Activity
*/

with 

projects as (
    select * from {{ ref('stg_gitlab_projects') }}
),

-- 1. 质量数据 (SonarQube)
sonar as (
    select 
        sp.gitlab_project_id,
        sm.bugs,
        sm.vulnerabilities,
        sm.coverage,
        sm.technical_debt_minutes,
        sm.quality_gate_status
    from {{ ref('stg_sonar_projects') }} sp
    join {{ ref('stg_sonar_measures') }} sm on sp.sonar_project_id = sm.sonar_project_id
    -- 仅取最新一次扫描
    where sm.analysis_date = (
        select max(analysis_date) from {{ ref('stg_sonar_measures') }} where sonar_project_id = sm.sonar_project_id
    )
),

-- 2. 交付数据 (Deployments & MRs)
delivery as (
    select
        project_id,
        count(*) filter (where environment = 'production' and status = 'success') as prod_deploy_count,
        count(*) filter (where status = 'failed') as failed_pipeline_count
    from {{ ref('stg_gitlab_deployments') }}
    group by 1
),

mr_summary as (
    select
        project_id,
        count(*) filter (where state = 'merged') as merged_mr_count,
        count(*) filter (where state = 'opened') as open_mr_backlog
    from {{ ref('stg_gitlab_merge_requests') }}
    group by 1
)

select
    p.gitlab_project_id,
    p.project_name,
    p.path_with_namespace,
    
    -- 质量指标
    coalesce(s.bugs, 0) as bug_count,
    coalesce(s.coverage, 0) as test_coverage_pct,
    round(coalesce(s.technical_debt_minutes, 0) / 60.0, 1) as tech_debt_hours,
    coalesce(s.quality_gate_status, 'UNKNOWN') as quality_gate,
    
    -- 产出指标
    coalesce(m.merged_mr_count, 0) as merged_mr_total,
    coalesce(m.open_mr_backlog, 0) as mr_backlog,
    coalesce(d.prod_deploy_count, 0) as prod_deploys,
    
    -- 综合健康分计算 (演示逻辑: 0-100)
    round(
        100 
        - (case when s.quality_gate_status = 'ERROR' then 30 else 0 end)
        - (least(coalesce(s.bugs, 0) * 2, 20))
        - (case when coalesce(s.coverage, 0) < 50 then (50 - s.coverage) else 0 end)
        + (least(coalesce(d.prod_deploy_count, 0) * 5, 20))
    ) as health_score
    
from projects p
left join sonar s on p.gitlab_project_id = s.gitlab_project_id
left join delivery d on p.gitlab_project_id = d.project_id
left join mr_summary m on p.gitlab_project_id = m.project_id
where p.is_archived = false
order by health_score desc
