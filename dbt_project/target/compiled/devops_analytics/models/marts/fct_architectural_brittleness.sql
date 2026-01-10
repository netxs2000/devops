/*
    架构脆性指数 (Architectural Brittleness Index - ABI)
    
    逻辑：
    1. 计算 In-Degree: 该项目产出的包被多少外部项目引用（影响力）。
    2. 结合复杂度 (Complexity) 和 覆盖率 (Coverage)。
    3. 识别“脆性核心”：高影响力、高复杂度、低覆盖率。
*/

with 

-- 1. 计算被引用情况
provision as (
    select 
        package_name,
        project_id
    from "devops_db"."public_staging"."stg_gitlab_packages"
),

consumption as (
    select
        dependency_name,
        count(distinct project_id) as consumer_count
    from "devops_db"."public_staging"."stg_gitlab_dependencies"
    group by 1
),

in_degree as (
    select
        p.project_id,
        sum(c.consumer_count) as total_in_degree
    from provision p
    join consumption c on p.package_name = c.dependency_name
    group by 1
),

-- 2. 质量指标
quality as (
    select 
        gitlab_project_id,
        complexity,
        cognitive_complexity,
        coverage
    from (
        select 
            sp.gitlab_project_id,
            sm.complexity,
            sm.cognitive_complexity,
            sm.coverage,
            row_number() over (partition by sp.gitlab_project_id order by sm.analysis_date desc) as rn
        from "devops_db"."public_staging"."stg_sonar_projects" sp
        join "devops_db"."public_staging"."stg_sonar_measures" sm on sp.sonar_project_id = sm.sonar_project_id
    ) t
    where rn = 1
)

select
    p.project_name,
    p.path_with_namespace,
    coalesce(i.total_in_degree, 0) as impact_in_degree,
    coalesce(q.complexity, 0) as complexity_score,
    coalesce(q.cognitive_complexity, 0) as cognitive_complexity,
    coalesce(q.coverage, 0) as coverage_pct,
    
    -- ABI 算法 (演示逻辑)
    round(
        (coalesce(i.total_in_degree, 0) * 10.0) + 
        (coalesce(q.cognitive_complexity, 0) / 2.0) - 
        (coalesce(q.coverage, 0))
    ) as brittleness_index,
    
    case 
        when coalesce(i.total_in_degree, 0) > 5 and coalesce(q.coverage, 0) < 30 then 'CRITICAL_BRITTLE_CORE'
        when coalesce(i.total_in_degree, 0) > 2 then 'STABLE_INFRA'
        else 'NORMAL'
    end as architectural_health_status

from "devops_db"."public_staging"."stg_gitlab_projects" p
left join in_degree i on p.gitlab_project_id = i.project_id
left join quality q on p.gitlab_project_id = q.gitlab_project_id
order by brittleness_index desc