/*
    SonarQube 质量扫描原子汇总 (SonarQube Quality Scans Intermediate)
    
    逻辑：
    1. 整合扫描度量值与项目元数据。
    2. 将 Sonar 项目对齐到 MDM 统一资产 ID。
    3. 单位转换（分钟 -> 小时）及核心指标清洗。
*/

with 

measures as (
    select * from "devops_db"."public_staging"."stg_sonar_measures"
),

projects as (
    select * from "devops_db"."public_staging"."stg_sonar_projects"
),

alignment as (
    select * from "devops_db"."public_intermediate"."int_entity_alignment"
),

joined as (
    select
        m.sonar_project_id,
        p.sonar_project_key,
        p.sonar_project_name,
        p.gitlab_project_id,
        -- 对齐到 MDM Master Entity ID
        coalesce(a.master_entity_id, 'UNKNOWN') as master_entity_id,
        
        m.analysis_date,
        date_trunc('day', m.analysis_date)::date as analysis_day,
        
        -- 开发语言产出 (LOC)
        m.ncloc,
        
        -- 质量门槛与缺陷
        m.quality_gate_status,
        m.bugs,
        m.vulnerabilities,
        m.code_smells,
        
        -- 复杂度
        m.complexity,
        m.cognitive_complexity,
        
        -- 测试覆盖率
        m.coverage,
        
        -- 技术债 (分钟转换为小时)
        round(m.technical_debt_minutes::numeric / 60.0, 2) as tech_debt_hours

    from measures m
    join projects p on m.sonar_project_id = p.sonar_project_id
    left join alignment a on p.gitlab_project_id = a.gitlab_project_id
)

select * from joined